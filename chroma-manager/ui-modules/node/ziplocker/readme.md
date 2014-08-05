#Introduction

Ziplocker is a tool to statically manage node.js dependencies. It enumerates a full dependency tree ala `npm shrinkwrap`
and saves unbuilt dependencies to a specified directory. It also allows for local module installation using the
`file://` specifier.

#Getting Started

The easiest way to list the directory where you want your dependencies to be stored is to export a `ZIPLOCK_DIR` ex:

  ```
    export ZIPLOCK_DIR=/Users/joegrund/projects/chroma/chroma-externals
  ```

This will tell ziplocker where to write dependencies to. If you would prefer not to export, you can specify an override
when invoking the program:

  ```
    $ ziplocker --overrides.ziplockDir=foo/bar/baz
  ```

Then you can install ziplocker globally (it also runs fine locally):

  ```
    $ cd chroma/chroma-manager/ui-modules/node/ziplocker
    $ npm i -g ./
  ```

#How to use

Zipping up dependencies.

  1. Navigate to the directory you want to ziplock.
  2. Run `ziplocker` in that directory.
  3. Commit Dependencies

Installing dependencies

  1. Navigate to the directory you want to install.
  2. Make sure you have run ziplocker in this dir previously.
  3. Run `zip-install`

Installing dev dependencies

  1. Navigate to the directory you want to install.
  2. Make sure you have run ziplocker in this dir previously.
  3. Run `zip-install-dev`
