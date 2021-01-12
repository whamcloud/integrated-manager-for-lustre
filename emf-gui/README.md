# EMF GUI

## Tech

- **Seed** - Rust framework, inspired by Elm. [Seed's Awesome list](https://github.com/MartinKavik/awesome-seed-rs).
- **[Seed Quickstart](https://github.com/MartinKavik/seed-quickstart-webpack)** - This project is based on this quickstart template.
- **[Tailwind CSS](https://tailwindcss.com/)** - CSS framework. All CSS classes in your project are typed for safe use in Rust code. Unused classes are automatically deleted for much smaller bundle size.
- **[Webpack](https://webpack.js.org/)** - Bundler. Auto-reload on code change, dev-server accessible from mobile phones, prerendering for static websites... and many more useful features are prepared for you in this quickstart.

## Dev Workflow

1. Ensure global deps are installed:

   - [Yarn](https://yarnpkg.com/lang/en/docs/install) - run `$ yarn -v` in terminal. It should output something like `1.17.3`
   - [Node.js](https://nodejs.org) - `$ node -v` => `v10.16.3`
   - [Rust](https://www.rust-lang.org/tools/install) - `$ rustc -V` => `rustc 1.38.0 (625451e37 2019-09-23)`
   - Rust target `wasm` - `$ rustup target list` => `.. wasm32-unknown-unknown (installed) ..`
     - Install: `$ rustup target add wasm32-unknown-unknown`
   - [wasm-pack](https://rustwasm.github.io/wasm-pack/)

     - Check: `$ wasm-pack -V` => `wasm-pack 0.8.1`
     - Install: `$ cargo install --force wasm-pack`

   - [cargo-make](https://sagiegurari.github.io/cargo-make/)

     - Check: `$ cargo make -V` => `cargo-make 0.22.1`
     - Install: `$ cargo install --force cargo-make`

1. Start dev-server:

   1. Open terminal in your project and go to directory `crate` - `$ cd emf-gui/crate`
   1. Install Webpack and other dependencies - `$ yarn`
   1. Start dev-server - `$ yarn start` - and then open [localhost:8000](http://localhost:8000) in a browser.
