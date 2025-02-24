# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased] - yyyy-mm-dd

## [1.1.4] - 2025-02-03

### Changed
- Improve error handling of ESI tasks

## 1.1.3 - 2025-01-25

### Added
- [Charlink](https://github.com/Maestro-Zacht/aa-charlink) integration

### Changed
- Tries to stop metenox updates to error at downtime

## [1.1.2] - 2024-11-09

### Added
- User agent when contacting the fuzzwork API

## 1.1.1 - 2024-10-24

### Changed
- adjust the default magmatic gas consumption to 110 per hour
  https://www.eveonline.com/news/view/patch-notes-version-22-01#h2-1

### Fixed
- typo in the `METENOX_MAGMATIC_GASES_PER_HOUR` setting

## 1.1.0 - 2024-10-14

### Changed
- **Rework of the permission system to be more modular. Most permissions need to be reassigned**
  Make sure to refer to the [README](README.md) to know how to properly assigne  them
- Updates the magmatic gases to the new hourly consumption
- Renamed the `metenox_update_all_owners` command to `metenox_update_all_holdings`

### Added
- Ability to add webhooks per corporations and manage when they should ping
- Ability to manually alter the hourly consumption of magmatic gases
- Metenox tags through the admin panel
- Analytics task

You can add it in your `local.py` file the following way:
```python
CELERYBEAT_SCHEDULE['metenox_send_daily_analytics'] = {
  'task': 'metenox.tasks.send_daily_analytics',
  'schedule': crontab(minute='0', hour='5')
}
```

### Fixed
- Issue 0ing all prices when querying prices from the API (see #3)
- Display both the value and the profit in the moons and metenox pages

## 1.0.9 - 2024-09-23

### Fixed
- Search bar in the metenox tab crashing
- Search bar in the corporation tab not working

## 1.0.8 - 2024-09-19

### Added
- Filtering options in the admin
- Admin display for owners
- Admin actions to enable/disable owners
- Displays the `last_updated` field in the admin view
- User/Admin notifications when an owner is disabled

### Fixed
- Properly updated the `last_updated` field of HoldingCorporation

## 1.0.7 - 2024-09-16

## Fixed
- Missing translation import in the price tab

## 1.0.6 - 2024-09-15

### Fixed
- Error when updating a corp without any structures

## 1.0.5 - 2024-09-15

### Added
- Display the owner/active owners count in the admin view

### Fixed
- Improve the error handling when corporations without metenoxes are being updated
- Possibility to have several owners

## 1.0.4 - 2024-09-11

### Added
- Footer under the corporation window
- Possibility to enable/disable owners in the  HoldingCorporation tab

### Fixed
- Moon material bay total volume calculation
- Moon material bay volume rounding
- Crash when a character without director role is trying to access the

## 1.0.3 - 2024-09-08

### Added
- More inlines in the Admin website

### Fixes
- block the ability to add objects in the admin tab
- fix an issue where a metenox created on a moon not in the moonmining module would never be estimated
- error when requesting a moon not in the moonmining application

## 1.0.2 - 2024-09-06

### Added
- Displays the owner characters in the admin webpage

### Fixed
- Doesn't return a None value for fuel prices on an empty database
- Add comments on TaskErrors

## 1.0.1 - 2024-09-05

### Fixed
- Fix an error 500 on moons without a scan registered
- Display negative isk values correctly
- Some modal fixs

## 1.0.0 - 2024-09-05

Initial release

### Added

- Calculates moon profit with metenox from the moonmining application
- Fetches Metenoxes information from corporations
  - Remaining fuel
  - Current status of the moon material bay
