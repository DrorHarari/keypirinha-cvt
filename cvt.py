import keypirinha as kp
import keypirinha_util as kpu
import json
import re
from pathlib import Path
import os
import sys
from cvt.safeeval import Parser

class Cvt(kp.Plugin):
    ITEMCAT_RESULT = kp.ItemCategory.USER_BASE + 1
    ITEM_LABEL_PREFIX = "Cvt: "

    CVTDEF_FILE = "cvtdefs.json"
    # Input parser definition
    RE_NUMBER = r'(?P<number>[-+]?[0-9]+(?:\.?[0-9]+)?(?:[eE][-+]?[0-9]+)?)'
    RE_FROM = r'(?P<from>[a-zA-Z]+[a-zA-Z0-9/]*)'
    RE_TO = r'(?P<to>[a-zA-Z]+[a-zA-Z0-9/]*)'
    INPUT_PARSER = f'^{RE_NUMBER}\s{RE_FROM}?(?P<done>\s)?{RE_TO}?'
    
    def __init__(self):
        super().__init__()

    def load_conversions(self, cvtdefs):
        try:
            defs_text = self.load_text_resource(cvtdefs)
            defs = json.loads(defs_text);
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
        self.load_conversions(self.CVTDEF_FILE)
        self.set_actions(self.ITEMCAT_RESULT, [
            self.create_action(
                name="copy",
                label="Copy",
                short_desc="Copy the converted units")])
        self.input_parser = re.compile(self.INPUT_PARSER)
        self.safeparser = Parser()

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

            self.set_catalog(catalog)

    def on_suggest(self, user_input, items_chain):
        parsed_input = self.input_parser.match(user_input) 
        if parsed_input is None:
            return

        in_number = float(parsed_input["number"])
        in_from = parsed_input["from"]
        in_done = (parsed_input["done"] or False) and len(parsed_input["done"]) > 0
        in_to = parsed_input["to"]

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

        cmp_exact = lambda candidate, alias: candidate == alias
        cmp_inexact = lambda candidate, alias: candidate in alias
        comperator = cmp_inexact if not in_done else cmp_exact

        check_from_unit_match = lambda u: not in_from or any([comperator(in_from, alias) for alias in u["aliases"]])
        check_to_unit_match = lambda u: not in_to or any([in_to in alias for alias in u["aliases"]])
        units = list(filter(check_from_unit_match, measure["units"]))
        
        if len(units) == 0:
            comperator = cmp_inexact
            units = list(filter(check_from_unit_match, measure["units"]))
        
        if len(units) == 1: # from unit was selected
            from_unit = units[0]
            
            for unit in measure["units"]:
                if not check_to_unit_match(unit):
                   continue
                    
                from_factor = self.evaluate_expr(from_unit["factor"])
                to_factor = self.evaluate_expr(unit["factor"])
                converted = in_number * from_factor / to_factor
                suggestions.append(self.create_item(
                    category=self.ITEMCAT_RESULT,
                    label=format(converted,".5f"),
                    short_desc=f'{unit["name"]} ({",".join(unit["aliases"])})',
                    target=format(converted,".5f"),
                    args_hint=kp.ItemArgsHint.REQUIRED,
                    hit_hint=kp.ItemHitHint.IGNORE,
                    data_bag=repr(converted)))
        else:
            for unit in units:
                from_factor = self.evaluate_expr(unit["factor"])
                converted = in_number / from_factor
                suggestions.append(self.create_item(
                    category=self.ITEMCAT_RESULT,
                    label=f"From {unit['name']}",
                    short_desc=f'Convert from {unit["name"]} ({",".join(unit["aliases"])})',
                    target=format(converted,".5f"),
                    args_hint=kp.ItemArgsHint.REQUIRED,
                    hit_hint=kp.ItemHitHint.IGNORE,
                    data_bag=format(converted,".5f")))

        self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)

    def on_execute(self, item, action):
        if item and item.category() == self.ITEMCAT_RESULT:
            kpu.set_clipboard(item.data_bag())