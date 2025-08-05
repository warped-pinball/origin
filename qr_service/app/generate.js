const QRCodeStyling = require('qr-code-styling');
const { createCanvas } = require('canvas');
const { JSDOM } = require('jsdom');

const options = JSON.parse(process.argv[2]);

const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
global.window = dom.window;
global.document = dom.window.document;
global.HTMLCanvasElement = dom.window.HTMLCanvasElement;

const qr = new QRCodeStyling({
  width: options.width,
  height: options.height,
  data: options.data,
  image: options.image,
  dotsOptions: options.dotsOptions,
  cornersSquareOptions: options.cornersSquareOptions,
  backgroundOptions: options.backgroundOptions,
});

qr.getRawData('svg').then((svg) => {
  process.stdout.write(svg.toString());
});
