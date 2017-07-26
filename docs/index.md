
# INSTALLATION

You can install webpack via npm:

    npm install webpack -g

> __Note:__ We’re installing webpack globally for demonstration purposes. When you are building a real application, it’s more advisable to install webpack as a `devDependency` of your project.


# GETTING STARTED

First, we’ll learn the basics of webpack by using just webpack’s command-line interface.


## Create a modular JavaScript project

Let’s create some modules in JavaScript, using the CommonJs syntax:

**cats.js**

    var cats = ['dave', 'henry', 'martha'];
    module.exports = cats;

**app.js (Entry Point)**

    cats = require('./cats.js');
    console.log(cats);

The "entry point" is where your application will start, and where webpack will start tracking dependencies between modules.


## webpack in 5 seconds

Give webpack the entry point (app.js) and specify an output file (app.bundle.js):

    webpack ./app.js app.bundle.js

webpack will read and analyze the entry point and its dependencies (including transitive dependencies). Then it will bundle them all into `app.bundle.js`.

<p align="center"><img src="https://dtinth.github.io/webpack-docs-images/usage/how-it-works.png" width="700" /></p>

Now your bundle is ready to be run. Run `node app.bundle.js` and marvel in your abundance of cats.

    node app.bundle.js
    ["dave", "henry", "martha"]

You can also use the bundle in the browser.


# GETTING SERIOUS

webpack is a very flexible module bundler. It offers a lot of advanced features, but not all features are exposed via the command-line interface. To gain full access to webpack’s flexibility, we need to create a "configuration file".

## Project structure

In real-world webpack projects, we’ll separate the source files from the bundled files by organizing them in folders. For example, we’ll put the source files in __src__, and bundled files in __bin__.

Our final project structure will look like this:

<p align="center"><img src="https://raw.githubusercontent.com/dtinth/webpack-docs-images/2459637650502958669ea6b11bf49dc0b3b083ae/usage/project-structure.png" width="700" /></p>

> In the wild, there are many project structures. Some projects use `app` instead of `src`. Some projects use `dist` or `build` instead of `bin`. Projects with tests usually use `test`, `tests`, `spec`, `specs` or colocate the test files in the source folder.

1. Create the `bin` and `src` directory.

    ```
    mkdir bin
    mkdir src
    ```

2. Move the original source files to the `src` folder.

    ```
    mv app.js cats.js src
    ```

3. Initialize an npm project.

    ```
    npm init # (answer the questions)
    ```

4. Install webpack as a development dependency. This lets your project declare the version of webpack it is compatible with.

    ```
    npm install --save-dev webpack
    ```


## Moving to a configuration file.

As your project grows and your configuration becomes more complex, it becomes unwieldy to configure webpack from the command line. Let’s create a configuration file instead.

1. Create `webpack.config.js`:

    ```js
    module.exports = {
        entry: './src/app.js',
        output: {
            path: './bin',
            filename: 'app.bundle.js'
        }
    };
    ```

    > A webpack configuration file is a CommonJS-style module. So you can run any kind of code here, as long as a configuration object is exported out of this module.

2. With the configuration file in place, you can now simply run webpack like this:

    ```
    webpack
    ```

    > webpack will read the configuration file, build the bundle, and save it as `bin/app.bundle.js`. If you examine webpack's output you'll see that it included both source files.

3. Run `bin/app.bundle.js` and you'll get your list of cats again.

    ```
    node bin/app.bundle.js
    ["dave", "henry", "martha"]
    ```

> You can also `require()` modules installed via npm with no extra configuration.


## Using loaders

webpack only supports JavaScript modules natively, but most people will be using a transpiler for ES2015, CoffeeScript, TypeScript, etc. They can be used in webpack by using [loaders](https://webpack.github.io/docs/using-loaders.html "Using Loaders").

Loaders are special modules webpack uses to 'load' other modules (written in another language) into JavaScript (that webpack understands). For example, [`babel-loader`](https://github.com/babel/babel-loader) uses Babel to load ES2015 files.

<p align="center"><img src="https://dtinth.github.io/webpack-docs-images/usage/babel-loader.png" width="700" /></p>

[`json-loader`](https://github.com/webpack/json-loader) loads JSON files (simply by prepending `module.exports =` to turn it into a CommonJs module).

<p align="center"><img src="https://dtinth.github.io/webpack-docs-images/usage/json-loader.png" width="700" /></p>

Loaders can be chained, and sometimes you need to chain loaders together. For example, [`yaml-loader`](https://github.com/okonet/yaml-loader) only converts YAML into JSON. Therefore, you need to chain it with `json-loader` so that it can be used.

<p align="center"><img src="https://dtinth.github.io/webpack-docs-images/usage/yaml-loader.png" width="700" /></p>

### Transpiling ES2015 using `babel-loader`

In this example, we're going to tell webpack to run our source files through [Babel](https://babeljs.io/) so we can use ES2015 features.

1. Install Babel and the presets:

    ```
    npm install --save-dev babel-core babel-preset-es2015
    ```

2. Install `babel-loader`:

    ```
    npm install --save-dev babel-loader
    ```

3. Configure Babel to use these presets by adding `.babelrc`

    ```
    { "presets": [ "es2015" ] }
    ```

4. Modify `webpack.config.js` to process all `.js` files using `babel-loader`.

    ```js
    module.exports = {
        entry: './src/app.js',
        output: {
            path: './bin',
            filename: 'app.bundle.js',
        },
        module: {
            loaders: [{
                test: /\.js$/,
                exclude: /node_modules/,
                loader: 'babel-loader'
            }]
        }
    }
    ```

    > We are excluding `node_modules` here because otherwise all external libraries will also go through Babel, slowing down compilation.

5. Install the libraries you want to use (in this example, jQuery):

    ```
    npm install --save jquery babel-polyfill
    ```

    > We are using `--save` instead of `--save-dev` this time, as these libraries will be used in runtime. We also use `babel-polyfill` so that ES2015 APIs are available in older browsers.

6. Edit `src/app.js`:

    ```js
    import 'babel-polyfill';
    import cats from './cats';
    import $ from 'jquery';

    $('<h1>Cats</h1>').appendTo('body');
    const ul = $('<ul></ul>').appendTo('body');
    for (const cat of cats) {
        $('<li></li>').text(cat).appendTo(ul);
    }
    ```

7. Bundle the modules using webpack:

    ```
    webpack
    ```

8. Add `index.html` so this app can be run in browser:

    ```html
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body>
            <script src="bin/app.bundle.js" charset="utf-8"></script>
        </body>
    </html>
    ```

When you open `index.html`, you should now see a list of cats!

<p align="center"><img src="https://dtinth.github.io/webpack-docs-images/usage/cats.png" width="700" /></p>

There are a number of [different loaders](https://webpack.github.io/docs/list-of-loaders.html "List of Loaders") you can use to include files in your app bundle, including css and image loaders.


## Using plugins

Usually you'll want to do some additional processing of the bundle in your workflow.  An example would be minifying your file so that clients can load it faster.  This can be done with [plugins](https://webpack.github.io/docs/using-plugins.html "Using Plugins").  We'll add the uglify plugin to our configuration:

	const webpack = require('webpack');

	module.exports = {
		entry: './src/app.js',
		output: {
			path: './bin',
			filename: 'app.bundle.js',
		},
		module: {
			loaders: [{
				test: /\.js?$/,
				exclude: /node_modules/,
				loader: 'babel-loader',
			}]
		},
		plugins: [
			new webpack.optimize.UglifyJsPlugin({
				compress: {
					warnings: false,
				},
				output: {
					comments: false,
				},
			}),
		]
	}

The Uglify plugin is included with webpack so you don't need to add additional modules, but this may not always be the case.  You can write your own [custom plugins](https://webpack.github.io/docs/how-to-write-a-plugin.html "How to write a Plugin").  For this build, the uglify plugin cut the bundle size from 1618 bytes to 308 bytes.


# FURTHER READING
* see [[CLI]] for the command line interface.
* see [[node.js API]] for the node.js interface.
* see [[Configuration]] for the configuration options.
..
