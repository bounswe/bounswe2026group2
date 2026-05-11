const { getMobileEnv } = require('./helpers/env');

const mobileEnv = getMobileEnv();
const appiumUrl = new URL(mobileEnv.APPIUM_SERVER_URL);

exports.config = {
  runner: 'local',
  hostname: appiumUrl.hostname,
  port: Number(appiumUrl.port || 4723),
  path: appiumUrl.pathname === '/' ? '/' : appiumUrl.pathname,

  specs: ['./specs/**/*.spec.js'],
  exclude: [],
  maxInstances: 1,

  capabilities: [
    {
      platformName: 'Android',
      'appium:automationName': 'UiAutomator2',
      'appium:deviceName': mobileEnv.ANDROID_DEVICE_NAME,
      'appium:app': mobileEnv.ANDROID_APP_PATH,
      'appium:autoGrantPermissions': true,
      'appium:newCommandTimeout': 120,
    },
  ],

  logLevel: 'info',
  bail: 0,
  waitforTimeout: 10_000,
  connectionRetryTimeout: 120_000,
  connectionRetryCount: 1,

  framework: 'mocha',
  reporters: [
    'spec',
    ['junit', {
      outputDir: './reports',
      outputFileFormat: () => 'mobile-e2e-report.xml',
    }],
  ],

  mochaOpts: {
    ui: 'bdd',
    timeout: 60_000,
  },
};
