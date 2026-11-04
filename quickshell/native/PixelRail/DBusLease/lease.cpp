#include <QtQml/QQmlExtensionPlugin>
#include <QtQml/qqml.h>
#include <QtDBus/QDBusConnection>
#include <QtDBus/QDBusConnectionInterface>
#include <QtDBus/QDBusReply>
#include <QtDBus/QDBusServiceWatcher>
#include <QtCore/QThread>
#include <QtGui/QFontDatabase>
#include <QtGui/QGuiApplication>
#include <QtGui/QRawFont>
#include "backlightwatch.hpp"
#include <private/qobject_p.h>
#include <private/qobject_p_p.h>

// Compatibility adapter ONLY for qs 0.3.2's persistent notification backend.
// Qt private metadata is read to locate its unparented service watcher; all actual
// changes use public Qt methods. Never access it with a different Qt build.
class NotificationLease : public QObject {
    Q_OBJECT
public:
    explicit NotificationLease(QObject *parent = nullptr) : QObject(parent) {}
    Q_INVOKABLE bool compatible() const { return QString::fromLatin1(qVersion()) == QString::fromLatin1(QT_VERSION_STR); }
    Q_INVOKABLE QString owner() const {
        auto *interface = QDBusConnection::sessionBus().interface();
        return interface ? interface->serviceOwner("org.freedesktop.Notifications").value() : QString();
    }
    Q_INVOKABLE bool guard() {
        if (!compatible()) return false;
        auto *object = QDBusConnection::sessionBus().objectRegisteredAt("/org/freedesktop/Notifications");
        if (!object || QByteArray(object->metaObject()->className()) != "qs::service::notifications::NotificationServer"
                || object->thread() != QThread::currentThread()) return false;
        auto *connections = QObjectPrivate::get(object)->connections.loadAcquire();
        QList<QDBusServiceWatcher*> watchers;
        if (connections) for (auto *connection = connections->senders; connection; connection = connection->next) {
            auto *watcher = qobject_cast<QDBusServiceWatcher*>(connection->sender);
            if (watcher && watcher->thread() == QThread::currentThread()
                    && watcher->watchedServices().contains("org.freedesktop.Notifications")) watchers.append(watcher);
        }
        // Disable only the notification-name auto-reclaim. Leave every other bus
        // subscription intact. Explicit mode transactions now own reacquisition.
        for (auto *watcher : watchers) watcher->removeWatchedService("org.freedesktop.Notifications");
        return true;
    }
    Q_INVOKABLE bool isOwner() const { return owner() == QDBusConnection::sessionBus().baseService(); }
    Q_INVOKABLE bool acquire() {
        if (!guard()) return false;
        auto bus = QDBusConnection::sessionBus(); auto *interface = bus.interface();
        if (!interface) return false;
        const auto existing = owner();
        if (existing == bus.baseService()) return true;
        if (!existing.isEmpty()) return false;
        auto reply = interface->registerService("org.freedesktop.Notifications",
            QDBusConnectionInterface::DontQueueService, QDBusConnectionInterface::DontAllowReplacement);
        return reply.isValid() && reply.value() == QDBusConnectionInterface::ServiceRegistered;
    }
    Q_INVOKABLE bool release() {
        if (!guard()) return false;
        auto bus = QDBusConnection::sessionBus();
        if (owner() != bus.baseService()) return owner().isEmpty();
        return bus.unregisterService("org.freedesktop.Notifications");
    }
};
// Passive system-bus events only: never starts a service or requests suspend.
class SystemEvents : public QObject {
    Q_OBJECT
    Q_PROPERTY(bool bluezAvailable READ bluezAvailable NOTIFY backendChanged)
public:
    explicit SystemEvents(QObject *parent=nullptr):QObject(parent) {
        auto bus=QDBusConnection::systemBus();
        auto *watcher=new QDBusServiceWatcher("org.bluez",bus,QDBusServiceWatcher::WatchForOwnerChange,this);
        connect(watcher,&QDBusServiceWatcher::serviceOwnerChanged,this,[this]{emit backendChanged();});
        bus.connect("org.freedesktop.login1","/org/freedesktop/login1","org.freedesktop.login1.Manager","PrepareForSleep",this,SLOT(prepareForSleep(bool)));
    }
    bool bluezAvailable() const {
        auto *interface=QDBusConnection::systemBus().interface();
        return interface && interface->isServiceRegistered("org.bluez").value();
    }
public slots:
    void prepareForSleep(bool sleeping) {if(!sleeping)emit resumed();}
signals:
    void resumed();
    void backendChanged();
};
class PixelTypography : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString family READ family CONSTANT)
public:
    explicit PixelTypography(QObject *parent=nullptr):QObject(parent) {}
    Q_INVOKABLE void apply(const QString &name) {if(name.isEmpty())return;QFont font(name);font.setPixelSize(14);QGuiApplication::setFont(font);}
    QString family() const {
        const auto families=QFontDatabase::families();
        for (const auto &name:{QStringLiteral("Google Sans Flex"),QStringLiteral("Roboto")}) {
            if(!families.contains(name))continue;
            const auto raw=QRawFont::fromFont(QFont(name));bool supported=raw.isValid();
            for(uint c=0x20;c<=0x7e && supported;++c)supported=raw.supportsCharacter(c);
            for(uint c=0x410;c<=0x44f && supported;++c)supported=raw.supportsCharacter(c);
            if(supported && raw.supportsCharacter(uint(0x401)) && raw.supportsCharacter(uint(0x451)))return name;
        }
        return {}; // Bundled, OFL-licensed Roboto is the QML fallback.
    }
};
class LeasePlugin : public QQmlExtensionPlugin {
    Q_OBJECT
    Q_PLUGIN_METADATA(IID QQmlExtensionInterface_iid)
public:
    void registerTypes(const char *uri) override { qmlRegisterType<NotificationLease>(uri, 1, 0, "NotificationLease"); qmlRegisterType<BacklightWatch>(uri,1,0,"BacklightWatch"); qmlRegisterType<SystemEvents>(uri,1,0,"SystemEvents"); qmlRegisterType<PixelTypography>(uri,1,0,"PixelTypography"); }
};
#include "lease.moc"
#include "backlightwatch.moc"
