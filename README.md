Keypirinha Plugin: Cvt
=========
# A universal unit converter for the Keypirinha launcher

This plugin for Keypirinha provides unit conversions for the following measures:

* Distance
* Area
* Volume
* Mass
* Speed
* Time
* Force
* Pressure
* Energy
* Power
* Fuel Consumption
* Temperature
* Data Size

## Usage ##
Make sure to install Keypirinha from http://keypirinha.com/

Open the LaunchBox and type:
```
Cvt <measure> <tab> <number> <space> <from-unit-optional> <to-unit-optional>
```

It may look complex but it is actually very easy and Cvt prompts you all the way. For example, to convert 12 inches to meters you type in the lauchbox:

```
Cvt <space> d <tab> 12 in mt <enter>
```

New conversions (including new measures) can be added in the cvtdefs.json file.

## Installation ##

Download the cvt.keypirinha-package pacakge file to the Keypirinha\portable\Profile\InstalledPackages folder

## Credits ##

* TBD

## Release Notes ##

**V 0.1**
- Initial release, rough around the edges.
- Known issues: temperatue and fuel consumption conversions are broken, some aliases are not enter-able.

**V 0.1.1**
- Fixed aliases to make them enter-able.
- Aliases selection is case sensitive - it should not be.

**V 0.2**
- Fix temperatue and fuel consumption conversions
- Aliases are no longer case sensitive
- A copy of cvtdef.json can be placed in the User folder for experimentation
- KNown issue: Keypirinha shows just 8 suggestions, when more than 8 units, some are not visible
