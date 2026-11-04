/* Surface-free, single-seat data-control test fixture. Never connects to a real compositor. */
#include <wayland-server.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "control.h"
struct source { struct wl_resource *resource; char *mimes[128]; int count; };
struct device { struct wl_resource *resource; struct wl_list link; };
static struct wl_list devices;
static struct source *selection;
static void destroy(struct wl_client *c, struct wl_resource *r) { (void)c; wl_resource_destroy(r); }
static void receive(struct wl_client *c, struct wl_resource *r, const char *mime, int32_t fd) {
    (void)c; struct source *s=wl_resource_get_user_data(r);
    if(s && s->resource) ext_data_control_source_v1_send_send(s->resource,mime,fd);
    close(fd);
}
static const struct ext_data_control_offer_v1_interface offer_impl={.receive=receive,.destroy=destroy};
static void announce(struct device *d) {
    struct wl_resource *offer=NULL;
    if(selection && selection->resource) {
        offer=wl_resource_create(wl_resource_get_client(d->resource),&ext_data_control_offer_v1_interface,1,0);
        wl_resource_set_implementation(offer,&offer_impl,selection,NULL);
        ext_data_control_device_v1_send_data_offer(d->resource,offer);
        for(int i=0;i<selection->count;i++) ext_data_control_offer_v1_send_offer(offer,selection->mimes[i]);
    }
    ext_data_control_device_v1_send_selection(d->resource,offer);
}
static void changed(void) { struct device *d; wl_list_for_each(d,&devices,link) announce(d); }
static void set_selection(struct wl_client *c, struct wl_resource *r, struct wl_resource *s) {
    (void)c;(void)r; struct source *old=selection;
    selection=s?wl_resource_get_user_data(s):NULL;
    if(old && old!=selection && old->resource) ext_data_control_source_v1_send_cancelled(old->resource);
    changed();
}
static void primary(struct wl_client *c, struct wl_resource *r, struct wl_resource *s) {(void)c;(void)r;(void)s;}
static const struct ext_data_control_device_v1_interface device_impl={.set_selection=set_selection,.destroy=destroy,.set_primary_selection=primary};
static void device_gone(struct wl_resource *r) {struct device *d=wl_resource_get_user_data(r);wl_list_remove(&d->link);free(d);}
static void source_gone(struct wl_resource *r) {
    struct source *s=wl_resource_get_user_data(r);s->resource=NULL;
    if(selection==s){selection=NULL;changed();}
    /* Offers may still reference s. Fixture lifetime bounds this small allocation. */
}
static void source_offer(struct wl_client *c,struct wl_resource *r,const char *mime) {
    (void)c;struct source *s=wl_resource_get_user_data(r);if(s->count<128)s->mimes[s->count++]=strdup(mime);
}
static const struct ext_data_control_source_v1_interface source_impl={.offer=source_offer,.destroy=destroy};
static void new_source(struct wl_client *c,struct wl_resource *r,uint32_t id) {
    (void)r;struct source *s=calloc(1,sizeof(*s));s->resource=wl_resource_create(c,&ext_data_control_source_v1_interface,1,id);
    wl_resource_set_implementation(s->resource,&source_impl,s,source_gone);
}
static void new_device(struct wl_client *c,struct wl_resource *r,uint32_t id,struct wl_resource *seat) {
    (void)r;(void)seat;struct device *d=calloc(1,sizeof(*d));d->resource=wl_resource_create(c,&ext_data_control_device_v1_interface,1,id);
    wl_resource_set_implementation(d->resource,&device_impl,d,device_gone);wl_list_insert(&devices,&d->link);
    announce(d);ext_data_control_device_v1_send_primary_selection(d->resource,NULL);
}
static const struct ext_data_control_manager_v1_interface manager_impl={.create_data_source=new_source,.get_data_device=new_device,.destroy=destroy};
static void bind_manager(struct wl_client *c,void *data,uint32_t version,uint32_t id) {
    (void)data;(void)version;struct wl_resource *r=wl_resource_create(c,&ext_data_control_manager_v1_interface,1,id);
    wl_resource_set_implementation(r,&manager_impl,NULL,NULL);
}
static const struct wl_seat_interface seat_impl={.release=destroy};
static void bind_seat(struct wl_client *c,void *data,uint32_t version,uint32_t id) {
    (void)data;struct wl_resource *r=wl_resource_create(c,&wl_seat_interface,version<5?version:5,id);
    wl_resource_set_implementation(r,&seat_impl,NULL,NULL);wl_seat_send_capabilities(r,0);
    if(version>=2)wl_seat_send_name(r,"seat0");
}
int main(void) {
    struct wl_display *display=wl_display_create();wl_list_init(&devices);
    wl_global_create(display,&wl_seat_interface,5,NULL,bind_seat);
    wl_global_create(display,&ext_data_control_manager_v1_interface,1,NULL,bind_manager);
    if(wl_display_add_socket(display,"pixelrail-clipboard-test")<0)return 1;
    wl_display_run(display);return 0;
}
