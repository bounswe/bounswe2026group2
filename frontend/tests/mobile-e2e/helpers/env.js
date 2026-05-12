const path = require('node:path');

require('dotenv').config({ path: path.resolve(__dirname, '..', '.env') });

const requiredEnv = [
  'ANDROID_APP_PATH',
  'APPIUM_SERVER_URL',
  'MOBILE_API_BASE_URL',
  'ANDROID_DEVICE_NAME',
];

function requireEnv(name) {
  const value = process.env[name];

  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }

  return value;
}

function resolveAppPath(appPath) {
  if (path.isAbsolute(appPath)) {
    return appPath;
  }

  return path.resolve(__dirname, '..', appPath);
}

function getMobileEnv() {
  const env = Object.fromEntries(requiredEnv.map((name) => [name, requireEnv(name)]));

  return {
    ...env,
    ANDROID_APP_PATH: resolveAppPath(env.ANDROID_APP_PATH),
  };
}

module.exports = {
  getMobileEnv,
  requiredEnv,
};
