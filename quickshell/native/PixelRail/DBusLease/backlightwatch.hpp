#pragma once
#include <QtCore/QObject>
#include <QtCore/QSocketNotifier>
#include <QtCore/QByteArray>
#include <sys/socket.h>
#include <linux/netlink.h>
#include <unistd.h>
#include <cerrno>

// Read-only kernel uevents, dispatched by Qt's existing event loop. No daemon/polling.
class BacklightWatch : public QObject {
    Q_OBJECT
    Q_PROPERTY(bool available READ available NOTIFY availableChanged)
    int socket_ = -1;
public:
    static bool isBacklightEvent(const QByteArray &message) {
        return message.split('\0').contains("SUBSYSTEM=backlight");
    }
    static bool isHardwareEvent(const QByteArray &message) {
        return isBacklightEvent(message) && message.split('\0').contains("SOURCE=hotkey");
    }
    explicit BacklightWatch(QObject *parent=nullptr):QObject(parent) {
        socket_=::socket(AF_NETLINK,SOCK_DGRAM|SOCK_NONBLOCK|SOCK_CLOEXEC,NETLINK_KOBJECT_UEVENT);
        if(socket_<0)return;
        sockaddr_nl address{};address.nl_family=AF_NETLINK;address.nl_groups=1;
        if(::bind(socket_,reinterpret_cast<sockaddr*>(&address),sizeof(address))!=0){::close(socket_);socket_=-1;return;}
        auto *notifier=new QSocketNotifier(socket_,QSocketNotifier::Read,this);
        connect(notifier,&QSocketNotifier::activated,this,[this,notifier]{
            bool changedBatch=false;bool hardwareBatch=false;
            for(int batch=0;batch<64;++batch){
                char buffer[16384];sockaddr_nl sender{};socklen_t length=sizeof(sender);
                const auto count=::recvfrom(socket_,buffer,sizeof(buffer),MSG_DONTWAIT,reinterpret_cast<sockaddr*>(&sender),&length);
                if(count<0){
                    if(errno==EAGAIN || errno==EWOULDBLOCK)break;
                    if(errno==EINTR)continue;
                    if(errno==ENOBUFS){changedBatch=true;break;}
                    notifier->setEnabled(false);::close(socket_);socket_=-1;emit availableChanged();return;
                }
                if(count==0)break;
                if(sender.nl_pid==0){const auto data=QByteArray(buffer,int(count));if(isBacklightEvent(data)){changedBatch=true;hardwareBatch=hardwareBatch || isHardwareEvent(data);}}
            }
            if(changedBatch)emit changed(hardwareBatch);
        });
    }
    ~BacklightWatch() override {if(socket_>=0)::close(socket_);}
    bool available() const {return socket_>=0;}
signals:
    void changed(bool hardware);
    void availableChanged();
};
