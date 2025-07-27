document.addEventListener('deviceready', function () {
  var logEl = document.getElementById('log');
  var urlEl = document.getElementById('current-url');
  function log(msg) {
    console.log(msg);
    if (logEl) {
      logEl.textContent += msg + '\n';
    }
  }

  function showUrl(url) {
    if (urlEl) {
      urlEl.textContent = url;
    }
  }

  // NFC
  if (window.nfc) {
    nfc.addNdefListener(function (nfcEvent) {
      try {
        var record = nfcEvent.tag.ndefMessage[0];
        var payload = nfc.bytesToString(record.payload);
        var url = payload.substring(1);
        log('NFC URL: ' + url);
      } catch (e) {
        log('NFC parse error: ' + e);
      }
    }, function () {
      log('NFC listener ready');
    }, function (err) {
      log('NFC error: ' + JSON.stringify(err));
    });
  }

  // Barcode scanner
  var scanBtn = document.getElementById('scan-btn');
  if (scanBtn) {
    scanBtn.addEventListener('click', function () {
      if (cordova && cordova.plugins && cordova.plugins.barcodeScanner) {
        cordova.plugins.barcodeScanner.scan(function (result) {
          if (!result.cancelled) {
            log('Scanned URL: ' + result.text);
          }
        }, function (error) {
          log('Scan failed: ' + error);
        }, { formats: 'QR_CODE' });
      }
    });
  }

  // Deep links
  if (window.deeplinks) {
    deeplinks.route({}).subscribe(function (match) {
      var url = match.$link.url;
      log('Deep link: ' + url);
      showUrl(url);
    }, function (nomatch) {
      log('No match: ' + JSON.stringify(nomatch));
    });
  }

  // UDP discovery of Warped Pinball devices
  var devicesEl = document.getElementById('devices');
  var knownDevices = {};
  var socketId = null;
  var DISCOVERY_PORT = 37020;
  var DEVICE_TIMEOUT = 60000;
  var ANNOUNCE_INTERVAL = DEVICE_TIMEOUT / 2;
  var PING_TIMEOUT = 2000;
  var STORAGE_KEY = 'knownDevices';
  var NETWORK_KEY = 'deviceNetwork';
  var FILE_NAME = 'devices.json';
  var networkId = null;
  var fileDir = null;

  if (window.resolveLocalFileSystemURL && cordova && cordova.file) {
    window.resolveLocalFileSystemURL(cordova.file.dataDirectory, function (dir) {
      fileDir = dir;
    });
  }

  function getNetworkId(ip) {
    if (!ip) return null;
    var parts = ip.split('.');
    if (parts.length >= 3) {
      return parts[0] + '.' + parts[1] + '.' + parts[2];
    }
    return ip;
  }

  function loadStoredDevices(cb) {
    function finish() {
      if (cb) cb();
      updateDevices();
    }

    if (window.resolveLocalFileSystemURL && cordova && cordova.file) {
      if (!fileDir) {
        window.resolveLocalFileSystemURL(cordova.file.dataDirectory, function (dir) {
          fileDir = dir;
          loadStoredDevices(cb);
        }, function () {
          knownDevices = {};
          finish();
        });
        return;
      }
      fileDir.getFile(FILE_NAME, { create: false }, function (file) {
        file.file(function (f) {
          var reader = new FileReader();
          reader.onloadend = function () {
            try {
              knownDevices = JSON.parse(this.result || '{}');
              Object.keys(knownDevices).forEach(function (ip) {
                knownDevices[ip].reachable = false;
              });
            } catch (e) {
              knownDevices = {};
            }
            if (!networkId) {
              networkId = localStorage.getItem(NETWORK_KEY);
            }
            finish();
          };
          reader.readAsText(f);
        });
      }, function () {
        knownDevices = {};
        finish();
      });
    } else {
      try {
        var saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
        knownDevices = saved;
        Object.keys(knownDevices).forEach(function (ip) {
          knownDevices[ip].reachable = false;
        });
        if (!networkId) {
          networkId = localStorage.getItem(NETWORK_KEY);
        }
      } catch (e) {
        knownDevices = {};
      }
      finish();
    }
  }

  function pingAll() {
    if (socketId === null) return;
    Object.keys(knownDevices).forEach(function (ip) {
      knownDevices[ip].reachable = false;
      var msg = JSON.stringify({ name: 'CordovaPOC', version: '1.0.0' });
      var buffer = new TextEncoder().encode(msg).buffer;
      chrome.sockets.udp.send(socketId, buffer, ip, DISCOVERY_PORT, function () {});
    });
    setTimeout(updateDevices, PING_TIMEOUT);
  }

  function updateDevices() {
    if (!devicesEl) return;
    var lines = [];
    Object.keys(knownDevices).forEach(function (ip) {
      var info = knownDevices[ip];
      var line = ip + ' - ' + info.name + ' (' + info.version + ')';
      if (!info.reachable) {
        line = '<span style="color: gray">' + line + '</span>';
      }
      lines.push(line);
    });
    devicesEl.innerHTML = lines.join('<br>');
    localStorage.setItem(STORAGE_KEY, JSON.stringify(knownDevices));
    if (networkId) {
      localStorage.setItem(NETWORK_KEY, networkId);
    }
    if (fileDir) {
      fileDir.getFile(FILE_NAME, { create: true }, function (file) {
        file.createWriter(function (writer) {
          writer.write(new Blob([JSON.stringify(knownDevices)], { type: 'application/json' }));
        });
      });
    }
  }

  function pruneDevices() {
    var now = Date.now();
    Object.keys(knownDevices).forEach(function (ip) {
      if (now - knownDevices[ip].lastSeen > DEVICE_TIMEOUT) {
        knownDevices[ip].reachable = false;
      }
    });
    updateDevices();
  }

  function announce() {
    if (socketId === null) return;
    pruneDevices();
    var msg = JSON.stringify({ name: 'Origin', version: '1.0.0' });
    var buffer = new TextEncoder().encode(msg).buffer;
    chrome.sockets.udp.send(socketId, buffer, '255.255.255.255', DISCOVERY_PORT, function () {});
    pingAll();
  }

  function startDiscovery() {
    if (!(window.chrome && chrome.sockets && chrome.sockets.udp)) {
      log('UDP sockets plugin not available');
      return;
    }
    chrome.sockets.udp.create({}, function (createInfo) {
      socketId = createInfo.socketId;
      chrome.sockets.udp.bind(socketId, '0.0.0.0', DISCOVERY_PORT, function () {
        chrome.sockets.udp.setBroadcast(socketId, true, function () {});
        if (chrome.sockets.udp.getInfo) {
          chrome.sockets.udp.getInfo(socketId, function (info) {
            networkId = getNetworkId(info.localAddress);
            var savedNetwork = localStorage.getItem(NETWORK_KEY);
            if (networkId !== savedNetwork) {
              knownDevices = {};
              localStorage.removeItem(STORAGE_KEY);
            }
            loadStoredDevices();
            pingAll();
          });
        } else {
          networkId = localStorage.getItem(NETWORK_KEY);
          loadStoredDevices();
          pingAll();
        }
        announce();
        setInterval(announce, ANNOUNCE_INTERVAL);
      });
    });

    chrome.sockets.udp.onReceive.addListener(function (info) {
      if (info.socketId !== socketId) return;
      var str = new TextDecoder().decode(new Uint8Array(info.data));
      try {
        var msg = JSON.parse(str);
        if (msg.name && msg.version) {
          if (!networkId) {
            networkId = getNetworkId(info.remoteAddress);
          }
          if (!knownDevices[info.remoteAddress]) {
            knownDevices[info.remoteAddress] = { name: msg.name, version: msg.version, lastSeen: Date.now(), reachable: true };
          } else {
            Object.assign(knownDevices[info.remoteAddress], { name: msg.name, version: msg.version, lastSeen: Date.now(), reachable: true });
          }
          updateDevices();
        }
      } catch (e) {
        // ignore malformed messages
      }
    });
  }

  startDiscovery();
});
