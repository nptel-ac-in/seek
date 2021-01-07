# \<nptel-pwa\>

nptel pwa app

## To Generate service worker

```
$ npm install
```
```
$ npm install --save-dev sw-precache
```
```
$ npm install -g gulp
```

```
$ gulp generate-service-worker
```

Run the above commands for generating service worker. Once generated, Add the additional path in urlsToCacheKeys for it to work with the
Existing structure. current path is '/modules/pwa/_static/nptel-pwa'

## Install the Polymer-CLI

First, make sure you have the [Polymer CLI](https://www.npmjs.com/package/polymer-cli) installed. Then run `polymer serve` to serve your application locally.

## Viewing Your Application

```
$ polymer serve
```

## Building Your Application

```
$ polymer build
```

This will create builds of your application in the `build/` directory, optimized to be served in production. You can then serve the built versions by giving `polymer serve` a folder to serve from:

```
$ polymer serve build/default
```

## Running Tests

```
$ polymer test
```

Your application is already set up to be tested via [web-component-tester](https://github.com/Polymer/web-component-tester). Run `polymer test` to run your application's test suite locally.
