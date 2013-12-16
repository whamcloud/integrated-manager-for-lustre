'use strict';

var fs = require('fs'),
  path = require('path'),
  format = require('util').format,
  navBarView = require('../views/nav-bar');


beforeEach(function() {
  navBarView.navigate();
  navBarView.loginToggle.click();
});

afterEach(function() {
  var passed = jasmine.getEnv().currentSpec.results().passed(),
    filePath = path.join(process.cwd(), 'failed-screen-shots');

  if (!passed) {
    browser.takeScreenshot().then(function(png) {
      fs.mkdir(filePath, function (e) {
        if(!e || (e && e.code === 'EEXIST')){
          var buf = new Buffer(png, 'base64'),
            description = jasmine.getEnv().currentSpec.description.replace(/\s/g, '-'),
            fileName = format('%s-%s.png', description, new Date().toISOString()),
            fileNameAndPath = path.join(filePath, fileName),
            stream = fs.createWriteStream(fileNameAndPath);

          stream.write(buf);
          stream.end();

          console.log('Saving screen shot to %s', fileNameAndPath);
        } else {
          console.log(e);
        }
      });
    });
  }
});
