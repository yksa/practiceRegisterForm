import Route from '@ember/routing/route';

export default class ListRoute extends Route {
    model(){
        return this.store.findAll('user');
    }
}
