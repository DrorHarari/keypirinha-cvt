import keypirinha as kp
import keypirinha_util as kpu
import json
import re
from pathlib import Path
import os
import sys
from .lib.safeeval import Parser

class Cvt(kp.Plugin):
    ITEMCAT_RESULT = kp.ItemCategory.USER_BASE + 1
    ITEMCAT_RELOAD_DEFS = kp.ItemCategory.USER_BASE + 2
    ITEM_LABEL_PREFIX = "Cvt: "

    CVTDEF_FILE = "cvtdefs.json"
    # Input parser definition
    RE_NUMBER = r'(?P<number>[-+]?[0-9]+(?:\.?[0-9]+)?(?:[eE][-+]?[0-9]+)?)'
    RE_FROM = r'(?P<from>[a-zA-Z]+[a-zA-Z0-9-/]*)'
    RE_TO = r'(?P<to>[a-zA-Z]+[a-zA-Z0-9-/]*)'
    INPUT_PARSER = f'^{RE_NUMBER}\s{RE_FROM}?(?P<done>\s)?{RE_TO}?'

    def __init__(self):
        super().__init__()

    def load_conversions(self):
        try:
            cvtdefs = os.path.join(kp.user_config_dir(), self.CVTDEF_FILE)
            if os.path.exists(cvtdefs):
                self.info(f"Loading custom config '{cvtdefs}'")
                self.customized_config = True
                with open(cvtdefs, "r") as f:
                    defs = json.load(f)                 
            else:
                self.customized_config = False
                cvtdefs = os.path.join("data/",self.CVTDEF_FILE)
                defs_text = self.load_text_resource(cvtdefs)
                defs = json.loads(defs_text)
        except Exception as exc:
            self.warn(f"Failed to load definitions file {cvtdefs}, {exc}")
            return

        self.measures = {measure["name"] : measure for measure in defs["measures"]}

    def evaluate_expr(self, expr):
        try:
            return float(self.safeparser.parse(expr).evaluate({}))
        except Exception as exc:
            self.warn(f"Failed to evaluate expression '{expr}', {exc}")
            return 1
            
    
    def on_start(self):
        self.input_parser = re.compile(self.INPUT_PARSER)
        self.safeparser = Parser()
        self.settings = self.load_settings()
        
        self.load_conversions()

        self.set_actions(self.ITEMCAT_RESULT, [
            self.create_action(
                name="copy",
                label="Copy",
                short_desc="Copy the converted units")])

        self.set_actions(self.ITEMCAT_RELOAD_DEFS, [
            self.create_action(
                name="reload",
                label="Reload",
                short_desc="Reload the custom definiion file")])


    def on_activated(self):
        pass

    def on_deactivated(self):
        pass

    def on_events(self, flags):
        if flags & kp.Events.PACKCONFIG:
            self.load_conversions()
            self.on_catalog()
        
    def on_catalog(self):
        catalog = []
        
        for name,measure in self.measures.items():
            catalog.append(self.create_item(
                category=kp.ItemCategory.REFERENCE,
                label=self.ITEM_LABEL_PREFIX + measure["name"],
                short_desc=measure["desc"],
                target=measure["name"],
                args_hint=kp.ItemArgsHint.REQUIRED,
                hit_hint=kp.ItemHitHint.NOARGS))

        if self.customized_config:
            catalog.append(self.create_item(
                category=self.ITEMCAT_RELOAD_DEFS,
                label=self.ITEM_LABEL_PREFIX + "Reload definitions",
                short_desc="Reload the custom definition file",
                target=measure["name"],
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.NOARGS))

        self.set_catalog(catalog)

    def do_conversion(self, in_number, from_unit, to_unit):
        from_factor = self.evaluate_expr(from_unit["factor"])
        from_offset = self.evaluate_expr(from_unit["offset"]) if "offset" in from_unit else 0
        to_factor = self.evaluate_expr(to_unit["factor"])
        to_offset = self.evaluate_expr(to_unit["offset"]) if "offset" in to_unit else 0

        if "inverse" in from_unit:
            if in_number == 0:
                in_number = 1e-30 # TBD better handle divide-by-zero 
            in_number = 1/in_number
        
        converted = (in_number-from_offset) * from_factor / to_factor + to_offset
        
        if "inverse" in to_unit:
            if converted == 0:
                converted = 1e-30
            converted = 1/converted
            
        return converted
        
    def on_suggest(self, user_input, items_chain):
        parsed_input = self.input_parser.match(user_input) 
        if parsed_input is None:
            return
        
        in_number = float(parsed_input["number"])
        in_from = parsed_input["from"]
        if in_from:
            in_from = in_from.lower()
        in_done = (parsed_input["done"] or False) and len(parsed_input["done"]) > 0
        in_to = parsed_input["to"]
        if in_to:
            in_to = in_to.lower()

        # Valid user input may be:
        # 1) number followed by whitespace
        # 2) (optionally) followed by a from-unit name
        # 3) (optionally) followed by a to-unit name

        if not items_chain:
            return

        current_item = items_chain[-1]
        measure = self.measures[current_item.target()]
        suggestions = []
        
        if not "units" in measure:
            return

        cmp_exact = lambda candidate, alias: candidate == alias.lower()
        cmp_inexact = lambda candidate, alias: candidate in alias.lower()
        comperator = cmp_inexact if not in_done else cmp_exact

        check_from_unit_match = lambda u: not in_from or any([comperator(in_from, alias) for alias in u["aliases"]])
        check_to_unit_match = lambda u: not in_to or any([in_to in alias for alias in u["aliases"]])
        units = list(filter(check_from_unit_match, measure["units"]))
        
        if len(units) == 0:
            comperator = cmp_inexact
            units = list(filter(check_from_unit_match, measure["units"]))
        
        if len(units) == 1: 
            # At this point we know the measure and the from unit
            # We propose the target units (filtered down if given to_unit)
            from_unit = units[0]
            
            for unit in measure["units"]:
                if not check_to_unit_match(unit):
                    continue
                    
                converted = self.do_conversion(in_number, from_unit, unit)
                suggestions.append(self.create_item(
                    category=self.ITEMCAT_RESULT,
                    label=format(converted,".5f"),
                    short_desc=f'{unit["name"]} ({",".join(unit["aliases"])})',
                    target=format(converted,".5f"),
                    args_hint=kp.ItemArgsHint.REQUIRED,
                    hit_hint=kp.ItemHitHint.IGNORE,
                    data_bag=repr(converted)))
        else:
            # At this point we know the measure but not the from unit
            for unit in units:
                from_factor = self.evaluate_expr(unit["factor"])
                converted = in_number / from_factor
                suggestions.append(self.create_item(
                    category=kp.ItemCategory.REFERENCE, #self.ITEMCAT_RESULT,
                    label=",".join(unit["aliases"]),
                    short_desc=f'Convert from {unit["name"]}',
                    target=format(converted,".5f")+"DSSDSDSD",
                    args_hint=kp.ItemArgsHint.REQUIRED,
                    hit_hint=kp.ItemHitHint.IGNORE,
                    data_bag=format(converted,".5f")))

        self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)

    def on_execute(self, item, action):
        if item and item.category() == self.ITEMCAT_RESULT:
            kpu.set_clipboard(item.data_bag())
        elif item and item.category() == self.ITEMCAT_RELOAD_DEFS:
            self.load_conversions()