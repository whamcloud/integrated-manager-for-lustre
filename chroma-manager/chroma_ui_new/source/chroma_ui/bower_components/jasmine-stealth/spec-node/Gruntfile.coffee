module.exports = (grunt) ->
  grunt.loadNpmTasks("grunt-jasmine-bundle")

  grunt.initConfig
    spec:
      unit:
        options:
          helpers: "spec/helpers/**/*.{js,coffee}",
          specs: "spec/**/*.{js,coffee}"
