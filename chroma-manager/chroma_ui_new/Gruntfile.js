/* jshint node: true */

module.exports = function (grunt) {
  'use strict';

  var config = {
    src: 'source/chroma_ui',
    dist: 'static/chroma_ui',
    baseDist: 'static',
    templateSource: 'templates_source/chroma_ui',
    templateDist: 'templates/chroma_ui',
    temp: 'tmp'
  };

  // load all grunt tasks
  require('matchdep').filterDev('grunt-*').forEach(grunt.loadNpmTasks);

  // load local tasks
  grunt.loadTasks('./tasks/');

  grunt.initConfig({
    config: config,

    filerev: {
      dist: {
        src: [
          '<%= config.dist %>/built.js',
          '<%= config.dist %>/built.css'
        ]
      }
    },

    watch: {
      less: {
        files: [
          '<%= config.src %>/**/*.less',
          '!<%= config.src %>/bower_components/**/*',
          '!<%= config.src %>/vendor/**/*'
        ],
        tasks: ['newer:less:dev']
      },
      jshint: {
        files: [
          '<%= config.src %>/**/*.js',
          'test/**/*.js',
          '!<%= config.src %>/bower_components/**/*.js',
          '!<%= config.src %>/vendor/**/*.js',
          '!test/matchers/matchers.js',
          '!coverage/**/*',
          '!**/node_modules/**/*'
        ],
        tasks: ['newer:jshint:all']
      }
    },

    less: {
      options: {
        paths: ['<%= config.src %>'],
        ieCompat: false
      },
      dev: {
        files: [{
          expand: true,
          cwd: '<%= config.src %>',
          src: ['styles/imports.less'],
          dest: '<%= config.dist %>',
          ext: '.css'
        }]
      },

      dist: {
        files: [{
          expand: true,
          cwd: '<%= config.src %>',
          src: ['styles/imports.less'],
          dest: '<%= config.temp %>/<%= config.dist %>',
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
          },
          {
            expand: true,
            cwd: '<%= config.src %>',
            dest: '<%= config.dist %>',
            src: [
              'bower_components/font-awesome/fonts/*'
            ]
          }
        ]
      }
    },

    karma: {
      unit: {
        configFile: 'karma.conf.js',
        singleRun: true,
        browsers: ['Chrome', 'Firefox', 'Safari']
      }
    },

    useminPrepare: {
      html: '<%= config.templateSource %>/base.html',
      options: {
        dest: './'
      }
    },

    usemin: {
      html: ['<%= config.templateDist %>/**/*.html'],
      css: ['<%= config.dist %>/**/*.css']
    },

    ngtemplates: {
      iml: {
        options: {
          url: function (url) {
            return url.replace(new RegExp('^' + config.src), '/' + config.dist);
          },
          usemin: '<%= config.dist %>/built.js',
          htmlmin:  {
            collapseWhitespace: true,
            collapseBooleanAttributes: true
          }
        },
        src: [
          '<%= config.src %>/**/*.html',
          '!<%= config.src %>/bower_components/**/*.html'
        ],
        dest: '<%= config.temp %>/templates.js'
      }
    },

    jshint: {
      options: {
        jshintrc: true
      },
      all: {
        src: '**/*.js'
      }
    }
  });

  grunt.registerTask('dev', [
    'clean:dev',
    'less:dev',
    'watch'
  ]);

  grunt.registerTask('precommit', [
    'jshint:all',
    'karma'
  ]);

  grunt.registerTask('dist', [
    'clean:dist',
    'less:dist',
    'useminPrepare',
    'cleanStaticTemplateString',
    'ngtemplates',
    'concat',
    'cssmin',
    'copy:dist',
    'uglify',
    'filerev',
    'usemin',
    'clean:postDist'
  ]);
};
