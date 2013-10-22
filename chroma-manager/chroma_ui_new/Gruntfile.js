/* jshint node: true */

module.exports = function (grunt) {
  'use strict';

  var config = {
    src: 'source/chroma_ui',
    dist: 'static/chroma_ui',
    baseDist: 'static',
    templateSource: 'templates_source/chroma_ui',
    templateDist: 'templates',
    temp: 'tmp'
  };

  // load all grunt tasks
  require('matchdep').filterDev('grunt-*').forEach(grunt.loadNpmTasks);

  // load local tasks
  grunt.loadTasks('./tasks/');

  grunt.initConfig({
    config: config,

    watch: {
      less: {
        files: ['<%= config.src %>/**/*.less', '!<%= config.src %>/bower_components/**/*'],
        tasks: ['less:dev']
      },
      livereload: {
        options: {
          livereload: true
        },
        files: [
          '<%= config.dist %>/**/*.css',
          '<%= config.src %>/**/*.html',
          '<%= config.src %>/**/*.js'
        ]
      },
      jshint: {
        tasks: ['jshint'],
        files: [
          '**/*.js',
          '!<%= config.src %>/bower_components/**/*.js',
          '!coverage/**/*',
          '!**/node_modules/**/*',
          '!<%= config.src %>/vendor/**/*.js'
        ],
        options: {
          spawn: false
        }
      },
      karma: {
        files: ['<%= config.src %>/**/*.js', 'test/**/*.js'],
        tasks: ['karma:dev:run']
      }
    },

    less: {
      options: {
        paths: ['<%= config.src %>/bower_components/', '<%= config.src %>/styles/', '.'],
        relativeUrls: true,
        ieCompat: false
      },
      dev: {
        files: [{
          expand: true,
          cwd: '<%= config.src %>',
          src: ['**/*.less', '!bower_components/**/*.less'],
          dest: '<%= config.dist %>',
          ext: '.css'
        }]
      },

      dist: {
        files: [{
          expand: true,
          cwd: '<%= config.src %>',
          src: ['**/*.less', '!bower_components/**/*.less'],
          dest: '<%= config.temp %>/chroma_ui',
          ext: '.css'
        }]
      }
    },

    clean: {
      dev: ['<%= config.dist %>', '<%= config.templateDist %>', 'coverage'],
      dist: ['<%= config.dist %>', '<%= config.temp %>', '<%= config.templateDist %>'],
      postDist: ['<%= config.temp %>']
    },

    copy: {
      dist: {
        files: [
          {
            expand: true,
            cwd: '<%= config.src %>',
            dest: '<%= config.dist %>',
            src: [
              'images/**/*'
            ]
          },
          {
            expand: true,
            cwd: '<%= config.templateSource %>',
            dest: '<%= config.templateDist %>',
            src: [
              '**/*.html'
            ]
          }
        ]
      }
    },

    karma: {
      dev: {
        background: true,
        configFile: 'karma.conf.js',
        browsers: ['Chrome', 'Firefox', 'Safari']
      }
    },

    useminPrepare: {
      html: '<%= config.templateSource %>/base.html',
      options: {
        dest: '<%= config.baseDist %>'
      }
    },

    usemin: {
      html: ['<%= config.templateDist %>/**/*.html'],
      css: ['<%= config.dist %>/**/*.css']
    },

    ngtemplates: {
      iml: {
        options: {
          templateConfig: function (file) {
            return file.replace(new RegExp('^' + config.src), config.dist);
          },
          concat: '<%= config.dist %>/built.js'
        },
        src: ['<%= config.src %>/**/*.html', '!<%= config.src %>/bower_components/**/*.html'],
        dest: '<%= config.tmp %>/templates.js'
      }
    },

    jshint: {
      options: {
        jshintrc: '.jshintrc'
      },
      all: [
        '**/*.js',
        '!<%= config.src %>/bower_components/**/*.js',
        '!coverage/**/*',
        '!**/node_modules/**/*',
        '!<%= config.src %>/vendor/**/*.js'
      ]
    }

  });

  // Handle jshint watching.
  var changedFiles = Object.create(null);
  var onChange = grunt.util._.debounce(function () {
    grunt.config(['jshint', 'all'], Object.keys(changedFiles));
    changedFiles = Object.create(null);
  }, 200);
  grunt.event.on('watch', function (action, filepath) {
    changedFiles[filepath] = action;
    onChange();
  });

  grunt.registerTask('dev', [
    'clean:dev',
    'less:dev',
    'karma:dev',
    'watch'
  ]);

  grunt.registerTask('dist', [
    'clean:dist',
    'less:dist',
    'jshint:all',
    'useminPrepare',
    'cleanStaticTemplateString',
    'ngtemplates',
    'concat',
    'cssmin',
    'copy:dist',
    'uglify',
    'usemin',
    'clean:postDist'
  ]);
};
