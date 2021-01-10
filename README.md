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

To convert a number of certain unit type:
```
<number> <from-unit-name>
```

Once the `from-unit-name` is typed, a list of units to convert to along with converted values is shown. At this point you can type a space (or any other non-alphanumeric character except /) and the target unit or select it from the list. Hit Enter to copy the converted value to the clipboard

**Mass Conversion Example**

![Example: convert 12 kg to other units](images/example-weight-conversion.png?raw=true)

**Temperature Conversion Example**

![Example: convert 103 degrees Fahrenheit to other units](images/example-temperature-conversion.png?raw=true)

To see a list of valid unit names for a given measure, type:
```
Cvt: <measure-name>
```
You don't need to remember the measure names - a list of measure names will be offered to select from. The list of units will include the full unit name as well as the conversion factor and offset (if applicable).

![Example: see mass measure units and their conversion rules](images/example-measure.png?raw=true)

## Customizing Conversions ##

You can add new conversion units and aliases to existing units via the Cvt.ini configuration file. To do so, just add a section based on the following pattern:

```
[unit/{measure name}/{unit name}]
factor = {expression to multiple the main unit by to get this unit}
aliases = {comma separate additional aliases}
offset = {number to substract after multiplying by factor}
inverse = {if true use the inverse of the factor}
```

For example, to add a "Finger" distance unit which is equivalent to 2 cm with the alias 'fg' we can use the following definition (note that for Distance, the reference unit is Meter as it has the conversion factor of 1.0 as can be seen by typing DISTANCE+<tab> in Keypirinha).

```
[unit/Distance/Finger]
factor = 2/100
aliases = fg
```

To add an alias "hdm" for Centimeters unit of distance measure use the following (note that the unit must be specified with exdact case):
```
[unit/distance/Centimetres]
aliases = hdm
```

## Adding New Conversions Measures ##

While one can add measures via the Cvt.ini file, if adding new measures with a lot of units, it is better to do it by means of a custom conversion definition file. Cvt maintains an internal conversion definition file called cvtdefs.json and you can export it to the User folder by entering the ```"Cvt: Customize coversions"``` action in the box. This will place a copy of the conversion definition file ```cvtdefs.json``` in the User configuration directory (```Keypirinha\portable\Profile\User```). Rename this file to, say, ```my-conversions.json``` and edit it, keeping the structure but leaving only the new measures you want to add. Then tell Cvt about it by adding a ```definitions``` items to the ```[main]``` section as in:

```
[main]
definition = 
    my-conversions.json
    another-conversion.json
```

If you want to create a conversion definition file that will add measures for a specific locale, you can use the name ```cvtdefs-{locale-name}.json```. For example, the file ```cvtdefs-ja_JP.json``` will be loaded in addition to what's loaded by other means when running on Japanese machine.

## Installation ##

The easiest way to install Cvt is to use the [PackageControl](https://github.com/ueffel/Keypirinha-PackageControl) plugin's InstallPackage command. 

For manual installation simply download the cvt.keypirinha-package file from the Releases page of this repository to:

* `Keypirinha\portable\Profile\InstalledPackages` in **Portable mode**

**Or** 

* `%APPDATA%\Keypirinha\InstalledPackages` in **Installed mode** 

## Credits ##

* Thanks the folks at [Quartic Software](http://www.quartic-software.co.uk/) for their awesome Android calculator app [RealCalc Plus](https://play.google.com/store/apps/details?id=uk.co.nickfines.RealCalcPlus) from which I took the list of measures, units and their conversion rules. If you like an HP-style RPN calculator in your phone, that's the one to use!
* Thanks [ArmaniKorsich](https://gitter.im/ArmaniKorsich) for the inspiration to write this plugin.
* Thanks [Shuzo Iwasaki](https://github.com/shuGH) for internationalization improvements.
* Thanks [vivancev86](https://github.com/vivancev86) for some speed units.

## Release Notes ##
**V2.2.1**
- Added the Dunam measure of area (=1000m^2).

**V2.2.0**
- Added aliases with '/' replaced by 'p' (e.g., l/100km can also be written as lphkm).
- When typing a measure name (e.g. Distance) and Tab one can now type a number and unit to convert. 

**V2.1.1**
- Added ```definitions``` configuration item in the ```[main]``` section of ```Cvt.ini``` to add custom conversion definition files. 
- Added ```decimal_separator``` configuration item in the ```[main]``` section of ```Cvt.ini``` to allow Cvt to use locale-specific numeric formatting on input and output. Valid values are ```dot``` (the default), ```comma``` and ```auto``` (based on Windows' regional settings).

**V2.0.0**
- BERAKING CHANGE. The format of the cvtdefs.json was simplified to enable conversion customizations via the Cvt.ini configuration file. The conversion from the old format is simple but in most cases, if the customization was just about adding some units, then the now just those units need to be added.
- New ```cvtdefs-{locale-name}.json``` pattern was added.
- New Cvt.ini boolean configuration item 'debug' added to the main section to troubleshoot conversion definition.
- New Cvt.ini string configuration item ```locale``` added to the main section to control the locale-specific version of ```cvtdefs-{locale}.json``` to load.
- Now it is possible to customize existing conversions and add new ones using the ```Cvt.ini``` configuration file (see there for examples).

**V1.0.3**
- Units with uppercase name where not matched on input. Fixed.
- Internal work, added debug message to ease troubelshooting.
- More aliases to temperatue units.

**V1.0.2**
- All units with US vs. Imperial versions such as fluid ounces (e.g, flozu vs. flozi or galu vs. gali) can now be used in their US version without the 'u' suffix (e.g, floz or gal).
- Previously, if a typed unit alias was also part of a longer unit alias, no conversion was shown. Now if there is an exact match with a unit alias, conversion is shown.
- New action to create conversion customization file (no longer needede to download it from this repository)

**V1.0.1**
- Support Keypirinha's space_as_tab=yes setting. No need for space after number so now 12kg is fine. To enter the target unit any non-alphanumeric character (other than /) can be used as separator. 

**V1.0**
- First formal release
- Made major change (simplification) to the usage 
- Add way to see available units as well as conversion factors and offsets (when applicable)
- Fixed errors in pressure and other conversions

**V0.2**
- Fix temperatue and fuel consumption conversions
- Aliases are no longer case sensitive
- A copy of cvtdef.json can be placed in the User folder for customization
- Known issue: Keypirinha shows just 8 suggestions, when more than 8 units, some are not visible but still available if you type the unit code

**V0.1.1**
- Fixed aliases to make them enter-able.
- Aliases selection is case sensitive - it should not be.

**V0.1**
- Initial release, rough around the edges.
- Known issues: temperatue and fuel consumption conversions are broken, some aliases are not enter-able.
