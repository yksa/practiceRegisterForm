import RESTAdapter from '@ember-data/adapter/rest';

export default RESTAdapter.extend({
  host: 'http://localhost:8888'
});