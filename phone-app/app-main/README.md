# Origin

Minimal Origin app demonstrating NFC, barcode scanning and deep-link handling.

## Screenshots

The screenshots below are generated automatically by the **Update Screenshots** workflow when changes are pushed to the `beta` branch. Each image corresponds to a page from the bottom navigation menu.

<p align="center">
  <img src="docs/screenshot-splash.png" alt="Splash" width="150" />
  <img src="docs/screenshot.png" alt="Scan" width="150" />
  <img src="docs/screenshot-profile.png" alt="Profile" width="150" />
  <img src="docs/screenshot-achievements.png" alt="Achievements" width="150" />
  <img src="docs/screenshot-shop.png" alt="Shop" width="150" />
  <img src="docs/screenshot-settings.png" alt="Settings" width="150" />
</p>

## Setup

```bash
git clone <repo>
cd app
npm ci
cordova platform add android ios
```

The pages in `www/` are generated from templates using:

```bash
npm run build:pages
```

This command runs automatically during `npm run prepare`.

### iOS signing

Edit `build.json` with your Apple developer team ID and provisioning profile so
the iOS build can be signed locally. In CI the workflow creates this file from
the secrets `IOS_TEAM_ID` and `IOS_PROFILE_UUID`. Set these secrets to your
Apple developer team ID and provisioning profile UUID.

```json
{
  "ios": {
    "release": {
      "codeSignIdentity": "iPhone Distribution",
      "developmentTeam": "<YOUR_TEAM_ID>",
      "packageType": "app-store",
      "provisioningProfile": "<PROFILE_UUID>"
    }
  }
}
```

### Android signing

The workflow generates a debug keystore automatically so the APK is signed and
installable without needing any secrets. The keystore uses the password
`android` and is stored as `debug.keystore`. If you want to use your own
keystore for distribution, edit `build.json` accordingly.

After building you can install the APK using `adb install`:

```bash
adb install platforms/android/app/build/outputs/apk/release/origin.apk
```

## Running

```bash
cordova emulate android   # or ios
```

Tag an NFC tag, scan a QR code or open a deep link to see the URL logged on the page.

## CI

Pull requests build a dev APK suffixed with `-dev<PR number>` so changes can be
tested easily. Merging to the `beta` branch creates a `-beta` release and
updates the screenshots. Pushing to `main` produces a production build with no
suffix. The workflow runs `npm test` before building to ensure generated pages
and Gradle patches work as expected. For Android the workflow generates a debug
keystore and runs `cordova build android --release --buildConfig build.json --
--packageType=apk` so an installable APK is produced without secrets. The iOS
job is currently disabled until signing credentials are configured. Set the
`IOS_TEAM_ID` and `IOS_PROFILE_UUID` secrets when you're ready to enable it.
Check the workflow run for downloadable APK and IPA files. When a release is
published, the workflow also uploads the APK as a release asset.

