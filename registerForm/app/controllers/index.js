import Controller from '@ember/controller';
import { action } from '@ember/object';

export default class SampleController extends Controller {

  @action
    saveUserInfo() {
      let  user = {name: this.get('name'), email: this.get('email'), password: this.get('password')}
      let newUser = this.store.createRecord('user', user);
      newUser.save();
      this.set('name','');
      this.set('email','');
      this.set('password','');
    }

  @action
    routeList() {
      this.transitionToRoute('user');
    }
}