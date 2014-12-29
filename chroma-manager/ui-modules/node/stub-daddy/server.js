'use strict';

var argv = require('yargs').argv;
var instance = require('./index')();

instance.webService.startService(argv);
