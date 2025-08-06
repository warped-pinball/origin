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

(async () => {
  const svg = await qr.getRawData('svg');
  let out;
  if (typeof svg === 'string') {
    out = svg;
  } else if (svg instanceof Buffer) {
    out = svg.toString();
  } else if (typeof svg.arrayBuffer === 'function') {
    const buf = Buffer.from(await svg.arrayBuffer());
    out = buf.toString();
  } else {
    throw new Error('Unsupported svg output');
  }
  process.stdout.write(out);
})();
