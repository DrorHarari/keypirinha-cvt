import keypirinha as kp
import keypirinha_wintypes as kpwt
import keypirinha_util as kpu
import traceback
import json
import re
import os
import locale
from .lib.safeeval import Parser


class Cvt(kp.Plugin):
    ITEMCAT_RESULT = kp.ItemCategory.USER_BASE + 1
    ITEMCAT_RELOAD_DEFS = kp.ItemCategory.USER_BASE + 2
    ITEMCAT_CREATE_CUSTOM_DEFS = kp.ItemCategory.USER_BASE + 3

    ITEM_LABEL_PREFIX = "Cvt: "
    UNIT_SECTION_PREFIX = "unit/"
    MEASURE_SECTION_PREFIX = "measure/"

    CVTDEF_FILE = "cvtdefs.json"
    CVTDEF_LOCALE_FILE = "cvtdefs-{}.json"

    def __init__(self):
        super().__init__()

    def get_separators(self):
        # [main] decimal_separator
        decimal_separator = "."
        thousand_separator = ""
        transmap_output = str.maketrans("", "", ",")
        config_decsep = self.settings.get_enum("decimal_separator", "main", fallback="dot", enum=["dot", "comma", "auto"])
        if config_decsep == "auto":
            thousand_separator = " "
            try:
                # use the GetLocaleInfoEx windows api to get the decimal and
                # thousand separators configured by system's user
                GetLocaleInfoEx = kpwt.declare_func(
                    kpwt.kernel32, "GetLocaleInfoEx", ret=kpwt.ct.c_int,
                    args=[kpwt.LPCWSTR, kpwt.DWORD, kpwt.PWSTR, kpwt.ct.c_int])
                LOCALE_SDECIMAL = 0x0000000E
                LOCALE_STHOUSAND = 0x0000000F

                # decimal separator
                buf = kpwt.ct.create_unicode_buffer(10)
                res = GetLocaleInfoEx(None, LOCALE_SDECIMAL, buf, len(buf))
                if res == 2 and len(buf.value) == res - 1 and buf.value == ",":
                    decimal_separator = ","
                # thousand separator
                # quite awful to have a try block here but we take advantage of
                # having GetLocaleInfoEx already defined
                try:
                    buf = kpwt.ct.create_unicode_buffer(10)
                    res = GetLocaleInfoEx(None, LOCALE_STHOUSAND, buf, len(buf))
                    if res == 2 and len(buf.value) == res - 1:
                        thousand_separator = buf.value
                except Exception:
                    traceback.print_exc()

                transmap_output = str.maketrans(".,", f"{decimal_separator}{thousand_separator}")
            except Exception:
                self.warn("Failed to get system user decimal and thousand separators. " +	# noqa
                          "Falling back to default (" + config_decsep + ")...")
                traceback.print_exc()
            self.info(f'Using "{decimal_separator}" as a decimal separator')
        if config_decsep == "comma":
            decimal_separator = ","
            thousand_separator = " "
            transmap_output = str.maketrans(".,", f"{decimal_separator}{thousand_separator}")

        return (decimal_separator, thousand_separator, transmap_output)

    def get_input_parser(self, decimal_sep):
        if decimal_sep != ",":
            decimal_sep = "\\."

        # Input parser definition
        RE_NUMBER = f'(?P<number>[-+]?[0-9]+(?:{decimal_sep}?[0-9]+)?(?:[eE][-+]?[0-9]+)?)'
        RE_FROM = r'(?P<from>[a-zA-Z]+[a-zA-Z0-9/]*)'
        DONE_FROM = r'(?P<done_from>[^a-zA-Z0-9/]+)'
        RE_TO = r'(?P<to>[a-zA-Z]+[a-zA-Z0-9/]*)'
        DONE_TO = r'(?P<done_to>[^a-zA-Z0-9/]+)'
        INPUT_PARSER = f'^{RE_NUMBER}(?=[^0-9])\\s*{RE_FROM}?{DONE_FROM}?{RE_TO}?{DONE_TO}?'

        return re.compile(INPUT_PARSER)

    def read_defs(self, defs_file):
        defs = None
        try:
            # Either file exist in the user profile dir
            cvtdefs = os.path.join(kp.user_config_dir(), defs_file)
            if os.path.exists(cvtdefs):
                self.info(f"Loading custom conversion definition file '{cvtdefs}'")
                self.customized_config = True
                with open(cvtdefs, "r", encoding="utf-8") as f:
                    defs = json.load(f)
            else:  # ... or it may be in the plugin
                try:
                    cvtdefs = os.path.join("data/", defs_file)
                    defs_text = self.load_text_resource(cvtdefs)
                    defs = json.loads(defs_text)
                    self.dbg(f"Loaded internal conversion definitions '{cvtdefs}'")
                except Exception as exc:
                    defs = {"measures": {}}
                    self.dbg(f"Did not load internal definitions file '{cvtdefs}', {exc}")
                    pass
        except Exception as exc:
            self.warn(f"Failed to load definitions file '{cvtdefs}', {exc}")

        return defs

    # Load measures, merging into existing ones
    def add_defs(self, defs):
        if "measures" in defs:
            def_measures = defs["measures"]
            for new_measure_name, new_measure in def_measures.items():
                new_measure_name = new_measure_name.lower()
                if new_measure_name not in self.measures:
                    self.measures[new_measure_name] = new_measure
                measure = self.measures[new_measure_name]
                for new_unit_name, new_unit in new_measure["units"].items():
                    if new_measure_name not in self.measure_aliases:
                        self.measure_aliases[new_measure_name] = {}
                    if new_unit_name not in measure["units"]:
                        measure["units"][new_unit_name] = new_unit
                    else:
                        if new_unit["factor"] != measure["units"][new_unit_name]["factor"]:
                            self.warn(f"Adding aliases to existing unit {new_unit_name} cannot change the unit factor")
                    for alias in new_unit["aliases"]:
                        alias = alias.lower()
                        if alias in self.all_units:
                            self.warn(f"Alias {alias} is defined multiple times for measure {new_measure_name}")
                        else:
                            unit = measure["units"][new_unit_name]
                            if alias not in unit["aliases"]:
                                unit["aliases"] = unit["aliases"] + [alias]
                        self.all_units[alias] = measure
                        self.measure_aliases[new_measure_name][alias] = measure

    # Units and aliaes can be customized in the cvt.ini file:
    # [unit/Distance/Finger]
    # factor = 0.02
    # aliases = fg
    # offset = 0
    # inverse" = false
    def read_setting_defs(self):
        defs = {"measures": {}}
        measures = defs["measures"]
        for section in self.settings.sections():
            if section.lower().startswith(self.UNIT_SECTION_PREFIX):
                measure_name, unit_name = section[len(self.UNIT_SECTION_PREFIX):].strip().split("/", 1)
                if measure_name not in measures:
                    measures[measure_name] = {
                        "desc": f"Convert units of area {measure_name}",
                        "units": {}
                    }
                measure = measures[measure_name]

                if unit_name not in measure["units"]:
                    measure["units"][unit_name] = {"aliases": []}
                unit = measure["units"][unit_name]

                unit["factor"] = self.settings.get_stripped("factor", section=section, fallback="1.0")

                offset = self.settings.get_stripped("offset", section=section, fallback=None)
                if offset:
                    unit["offset"] = self.settings.get_stripped("offset", section=section, fallback=None)

                inverse = self.settings.get_bool("inverse", section=section, fallback=None)
                if inverse:
                    unit["inverse"] = self.settings.get_bool("inverse", section=section, fallback=None)

                aliases = self.settings.get_stripped("aliases", section=section, fallback=None)
                if aliases:
                    unit["aliases"] = unit["aliases"] + self.settings.get_stripped('aliases', section=section, fallback=None).split(",")

                self.dbg(f"Added unit {unit_name} for measure {measure_name} as:\n{repr(unit)}")
            elif section.lower().startswith(self.MEASURE_SECTION_PREFIX):
                measure_name = section[len(self.MEASURE_SECTION_PREFIX):].strip()
                if measure_name not in measures:
                    measures[measure_name] = {"units": {}}
                measure = measures[measure_name]
                measure["desc"] = self.settings.get_stripped("desc", section=section, fallback=f"Convert units of area {measure_name}")

                self.dbg(f"Added configured measure {measure_name}")

        return defs

    def reconfigure(self):
        self.settings = self.load_settings()
        self._debug = self.settings.get_bool("debug", "main", False)
        self.customized_config = False
        self.dbg("CVT: Reloading. Debug enabled")

        self.decimal_separator, self.thousand_separator, self.transmap_output = self.get_separators()
        locale_name = self.settings.get("locale", "main", locale.getdefaultlocale()[0])

        self.input_parser = self.get_input_parser(self.decimal_separator)

        self.all_units = {}
        self.measures = {}
        self.measure_aliases = {}

        defs = self.read_defs(self.CVTDEF_FILE)
        if defs:
            self.add_defs(defs)

        locale_specific_def = self.CVTDEF_LOCALE_FILE.format(locale_name)
        defs = self.read_defs(locale_specific_def)
        if defs:
            self.add_defs(defs)

        self.definitions = self.settings.get_multiline("definitions", "main", fallback=[], keep_empty_lines=False)
        for definition_files in self.definitions:
            defs = self.read_defs(definition_files)
            if defs:
                self.add_defs(defs)

        defs = self.read_setting_defs()
        if defs:
            self.add_defs(defs)

    def evaluate_expr(self, expr):
        try:
            return float(self.safeparser.parse(expr).evaluate({}))
        except Exception as exc:
            self.warn(f"Failed to evaluate expression '{expr}', {exc}")
            return 1

    def on_start(self):
        self.safeparser = Parser()

        self.reconfigure()

        self.set_actions(self.ITEMCAT_RESULT, [
            self.create_action(
                name="copy",
                label="Copy",
                short_desc="Copy the converted units")])

        self.set_actions(self.ITEMCAT_RELOAD_DEFS, [
            self.create_action(
                name="reload",
                label="Reload",
                short_desc="Reload the custom conversion definition file")])

        self.set_actions(self.ITEMCAT_CREATE_CUSTOM_DEFS, [
            self.create_action(
                name="customize",
                label="Customize coversions",
                short_desc="Create a custom conversion definition file")])

    def on_activated(self):
        pass

    def on_deactivated(self):
        pass

    def on_events(self, flags):
        if flags & kp.Events.PACKCONFIG:
            self.reconfigure()
            self.on_catalog()

    def on_catalog(self):
        catalog = []

        # To discover measures and units, type CVT then proposed supported measures
        for name, measure in self.measures.items():
            catalog.append(self.create_item(
                category=kp.ItemCategory.REFERENCE,
                label=self.ITEM_LABEL_PREFIX + name.title(),
                short_desc=measure["desc"],
                target=name,
                args_hint=kp.ItemArgsHint.REQUIRED,
                hit_hint=kp.ItemHitHint.NOARGS))

        # When custom conversion definition is used, propose Reload option
        if self.customized_config:
            catalog.append(self.create_item(
                category=self.ITEMCAT_RELOAD_DEFS,
                label=self.ITEM_LABEL_PREFIX + "Reload custom conversions",
                short_desc="Reload the custom conversions file",
                target="ITEMCAT_RELOAD_DEFS",
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.IGNORE))
        else:  # Else offer an option to customize
            catalog.append(self.create_item(
                category=self.ITEMCAT_CREATE_CUSTOM_DEFS,
                label=self.ITEM_LABEL_PREFIX + "Customize conversions",
                short_desc="Create a custom conversion definition file",
                target="ITEMCAT_CREATE_CUSTOM_DEFS",
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.IGNORE))

        self.set_catalog(catalog)

    def do_conversion(self, in_number, from_unit, to_unit):
        from_factor = self.evaluate_expr(from_unit["factor"])
        from_offset = self.evaluate_expr(from_unit["offset"]) if "offset" in from_unit else 0
        to_factor = self.evaluate_expr(to_unit["factor"])
        to_offset = self.evaluate_expr(to_unit["offset"]) if "offset" in to_unit else 0

        if "inverse" in from_unit:
            if in_number == 0:
                in_number = 1e-30  # TBD better handle divide-by-zero
            in_number = 1 / in_number

        converted = (in_number - from_offset) * from_factor / to_factor + to_offset

        if "inverse" in to_unit:
            if converted == 0:
                converted = 1e-30
            converted = 1 / converted

        return converted

    def on_suggest(self, user_input, items_chain):
        parsed_input = self.input_parser.match(user_input)
        self.dbg(f"In suggest, parsed input = '{parsed_input}'")
        if parsed_input is None and len(items_chain) < 1:
            self.dbg("In suggest, not matched")
            return

        in_from = ""
        if parsed_input:
            # We have a number and (maybe) units
            matched_number = parsed_input["number"]
            if self.decimal_separator != ".":
                matched_number = matched_number.replace(self.decimal_separator, ".")

            in_number = float(matched_number)

            in_from = parsed_input["from"]
            if in_from:
                in_from = in_from.lower()
            # in_done_from = (parsed_input["done_from"] or False) and len(parsed_input["done_from"]) > 0
            in_to = parsed_input["to"]
            in_done_to = (parsed_input["done_to"] or False) and len(parsed_input["done_to"]) > 0
            if in_to:
                in_to = in_to.lower()

        # User selected one of Cvt's Measures - show unit suggestions
        all_units = self.all_units
        measure = None
        if len(items_chain) == 1:
            if not items_chain[0].target() in self.measures:
                return

            measure_name = items_chain[0].target()
            measure = self.measures[measure_name]

            all_units = self.measure_aliases[measure_name]
            if not parsed_input or (in_from and not(in_from in all_units.keys())):
                self.dbg(f"on_suggest: No parsed input, measure = {measure}")

                suggestions = []
                for unit_name, unit in measure["units"].items():
                    conv_hint = f"factor {unit['factor']}"
                    if "offset" in unit:
                        conv_hint = conv_hint + f", offset {unit['offset']}"
                    self.dbg(f"Added suggestion for unit '{unit_name}' conv_hint = {conv_hint}")
                    suggestions.append(self.create_item(
                        category=kp.ItemCategory.REFERENCE,
                        label=",".join(unit["aliases"]),
                        short_desc=f'Conversion unit {unit_name}, {conv_hint}',
                        target=unit_name,
                        args_hint=kp.ItemArgsHint.FORBIDDEN,
                        hit_hint=kp.ItemHitHint.IGNORE))

                self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)
                return

        if in_from in all_units:
            measure = all_units[in_from]
        else:
            self.dbg(f"reject in_from = {in_from}, units = {all_units.keys()}")
            return

        if "units" not in measure:
            return

        cmp_exact = lambda candidate, alias: candidate == alias.lower()		# noqa
        cmp_inexact = lambda candidate, alias: candidate in alias.lower()	# noqa
        comperator = cmp_exact

        check_from_unit_match = \
			lambda u: not in_from or any([comperator(in_from, alias) for alias in u["aliases"]])	# noqa
        check_to_unit_match = \
			lambda u: not in_to or any([comperator(in_to, alias) for alias in u["aliases"]])	# noqa
        units = list(filter(check_from_unit_match, measure["units"].values()))

        if len(units) == 0:
            comperator = cmp_inexact
            units = list(filter(check_from_unit_match, measure["units"].values()))

        self.dbg(f"#units matched = {len(units)}")
        suggestions = []
        if len(units) == 1:
            # At this point we know the measure and the from unit
            # We propose the target units (filtered down if given to_unit)
            from_unit = units[0]

            for unit_name, unit in measure["units"].items():
                self.dbg(f"unit = {unit_name}")
                comperator = cmp_exact if in_done_to else cmp_inexact
                if not check_to_unit_match(unit):
                    continue

                self.add_conversion_result(suggestions, from_unit, unit, unit_name, in_number)

        self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)

    def add_conversion_result(self, suggestions, from_unit, to_unit, to_unit_name, in_number):
        self.dbg(f"Adding conversion result to {to_unit_name}")
        converted = self.do_conversion(in_number, from_unit, to_unit)

        converted_display = f"{converted:,.9g}".translate(self.transmap_output)
        converted_clipboard = f"{converted:.9g}"
        if self.decimal_separator != ".":
            converted_clipboard = converted_clipboard.replace(".", self.decimal_separator)

        suggestions.append(self.create_item(
            category=self.ITEMCAT_RESULT,
            label=converted_display,
            short_desc=f'{to_unit_name} ({",".join(to_unit["aliases"])})',
            target=converted_display,
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.IGNORE,
            data_bag=converted_clipboard))

    def on_execute(self, item, action):
        if item and item.category() == self.ITEMCAT_RESULT:
            kpu.set_clipboard(item.data_bag())
        elif item and item.category() == self.ITEMCAT_RELOAD_DEFS:
            self.reconfigure()
            self.on_catalog()
        elif item and item.category() == self.ITEMCAT_CREATE_CUSTOM_DEFS:
            try:
                builtin_cvtdefs = os.path.join("data/", self.CVTDEF_FILE)
                builtin_cvtdefs_text = self.load_text_resource(builtin_cvtdefs).replace("\r\n", "\n")
                custom_cvtdefs = os.path.join(kp.user_config_dir(), self.CVTDEF_FILE)
                if os.path.exists(custom_cvtdefs):
                    self.warn(f"Customized conversion file '{custom_cvtdefs}' already exists. It hasn't been overwritten")
                else:
                    with open(custom_cvtdefs, "w", encoding="utf-8") as f:
                        f.write(builtin_cvtdefs_text)
                        f.close()
                    kpu.explore_file(custom_cvtdefs)
                    self.reconfigure()
                    self.on_catalog()
            except Exception as exc:
                self.warn(f"Failed to create custom conversion definition file '{custom_cvtdefs}', {exc}")
