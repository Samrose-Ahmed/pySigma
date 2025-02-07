from uuid import UUID
from wsgiref.validate import validator

import pytest
from sigma.collection import SigmaCollection
from sigma.exceptions import SigmaValueError
from sigma.modifiers import SigmaAllModifier, SigmaBase64OffsetModifier, SigmaContainsModifier
from sigma.rule import SigmaDetectionItem, SigmaRule, SigmaRuleTag
from sigma.types import SigmaString
from sigma.validators.metadata import IdentifierCollisionIssue, IdentifierExistenceIssue, IdentifierExistenceValidator, IdentifierUniquenessValidator
from sigma.validators.condition import DanglingDetectionIssue, DanglingDetectionValidator
from sigma.validators.modifiers import AllWithoutContainsModifierIssue, Base64OffsetWithoutContainsModifierIssue, InvalidModifierCombinationsValidator, ModifierAppliedMultipleIssue
from sigma.validators.tags import ATTACKTagValidator, InvalidATTACKTagIssue, InvalidTLPTagIssue, TLPTagValidator, TLPv1TagValidator, TLPv2TagValidator
from sigma.validators.values import ControlCharacterIssue, ControlCharacterValidator, DoubleWildcardIssue, DoubleWildcardValidator, NumberAsStringIssue, NumberAsStringValidator, WildcardInsteadOfEndswithIssue, WildcardInsteadOfStartswithIssue, WildcardsInsteadOfContainsModifierIssue, WildcardsInsteadOfModifiersValidator

@pytest.fixture
def rule_without_id():
    return SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        selection:
            field: value
        condition: selection
    """)

@pytest.fixture
def rule_with_id():
    return SigmaRule.from_yaml("""
    title: Test
    id: 19855ce4-00b3-4d07-8e57-f6c6955ce4e7
    status: test
    logsource:
        category: test
    detection:
        selection:
            field: value
        condition: selection
    """)

@pytest.fixture
def rules_with_id_collision():
    return [
        SigmaRule.from_yaml(f"""
        title: Test {i}
        id: 32532a0b-e56c-47c9-bcbb-3d88bd670c37
        status: test
        logsource:
            category: test
        detection:
            selection:
                field{i}: value{i}
            condition: selection
        """)
        for i in range(2)
    ]

def test_validator_identifier_existence(rule_without_id):
    validator = IdentifierExistenceValidator()
    assert validator.validate(rule_without_id) == [ IdentifierExistenceIssue([rule_without_id]) ] and \
        validator.finalize() == []

def test_validator_identifier_existence_valid(rule_with_id):
    validator = IdentifierExistenceValidator()
    assert validator.validate(rule_with_id) == [] and \
        validator.finalize() == []

def test_validator_identifier_uniqueness(rules_with_id_collision):
    validator = IdentifierUniquenessValidator()
    assert [
        issue
        for rule in rules_with_id_collision
        for issue in validator.validate(rule)
    ] == [] and \
        validator.finalize() == [ IdentifierCollisionIssue(rules_with_id_collision, UUID("32532a0b-e56c-47c9-bcbb-3d88bd670c37")) ]

def test_validator_dangling_detection():
    validator = DanglingDetectionValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        referenced1:
            field1: val1
        referenced2:
            field2: val2
        referenced3:
            field3: val3
        unreferenced:
            field4: val4
        condition: (referenced1 or referenced2) and referenced3
    """)
    assert validator.validate(rule) == [ DanglingDetectionIssue([rule], "unreferenced") ]

def test_validator_dangling_detection_valid():
    validator = DanglingDetectionValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        referenced1:
            field1: val1
        referenced2:
            field2: val2
        referenced3:
            field3: val3
        condition: (referenced1 or referenced2) and referenced3
    """)
    assert validator.validate(rule) == []

def test_validator_dangling_detection_valid_x_of_wildcard():
    validator = DanglingDetectionValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        referenced1:
            field1: val1
        referenced2:
            field2: val2
        referenced3:
            field3: val3
        condition: 1 of referenced*
    """)
    assert validator.validate(rule) == []

def test_validator_dangling_detection_valid_x_of_them():
    validator = DanglingDetectionValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        referenced1:
            field1: val1
        referenced2:
            field2: val2
        referenced3:
            field3: val3
        condition: 1 of them
    """)
    assert validator.validate(rule) == []

def test_validator_double_wildcard():
    validator = DoubleWildcardValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field1: te**st
            field2: 123
        condition: sel
    """)
    assert validator.validate(rule) == [ DoubleWildcardIssue([ rule ], SigmaString("te**st")) ]

def test_validator_double_wildcard_valid():
    validator = DoubleWildcardValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field1: t*es*t
            field2: 123
        condition: sel
    """)
    assert validator.validate(rule) == []

def test_validator_number_as_string():
    validator = NumberAsStringValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field1: 123
            field2: "234"
        condition: sel
    """)
    assert validator.validate(rule) == [ NumberAsStringIssue([ rule ], SigmaString("234")) ]

def test_validator_control_characters():
    validator = ControlCharacterValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field1: "\\temp"
            field2: "\\\\test"
        condition: sel
    """)
    assert validator.validate(rule) == [ ControlCharacterIssue([ rule ], SigmaString("\temp"))]

def test_validator_wildcards_instead_of_contains():
    validator = WildcardsInsteadOfModifiersValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field:
              - "*val1*"
              - "*val2*"
              - "*val3*"
        condition: sel
    """)
    assert validator.validate(rule) == [
        WildcardsInsteadOfContainsModifierIssue(
            [ rule ],
            SigmaDetectionItem("field", [], [
                    SigmaString("*val1*"),
                    SigmaString("*val2*"),
                    SigmaString("*val3*"),
                    ]
                )
            )
        ]

def test_validator_wildcard_instead_of_endswith():
    validator = WildcardsInsteadOfModifiersValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field:
              - "*val1"
              - "*val2"
              - "*val3"
        condition: sel
    """)
    assert validator.validate(rule) == [
        WildcardInsteadOfEndswithIssue(
            [ rule ],
            SigmaDetectionItem("field", [], [
                    SigmaString("*val1"),
                    SigmaString("*val2"),
                    SigmaString("*val3"),
                    ]
                )
            )
        ]

def test_validator_wildcard_instead_of_startswith():
    validator = WildcardsInsteadOfModifiersValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field:
              - "val1*"
              - "val2*"
              - "val3*"
        condition: sel
    """)
    assert validator.validate(rule) == [
        WildcardInsteadOfStartswithIssue(
            [ rule ],
            SigmaDetectionItem("field", [], [
                    SigmaString("val1*"),
                    SigmaString("val2*"),
                    SigmaString("val3*"),
                    ]
                )
            )
        ]

def test_validator_wildcards_instead_of_modifiers_inconsistent():
    validator = WildcardsInsteadOfModifiersValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field:
              - "*val1*"
              - "*val2"
              - "val3*"
        condition: sel
    """)
    assert validator.validate(rule) == [ ]

def test_validator_all_without_contains():
    validator = InvalidModifierCombinationsValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field|all:
                - value1
                - value2
                - value3
        condition: sel
    """)
    assert validator.validate(rule) == [
        AllWithoutContainsModifierIssue(
                [ rule ],
                SigmaDetectionItem("field", [ SigmaAllModifier ], [ "value1", "value2", "value3" ])
            )
        ]

def test_validator_all_without_contains_unbound():
    validator = InvalidModifierCombinationsValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            "|all":
                - value1
                - value2
                - value3
        condition: sel
    """)
    assert validator.validate(rule) == [ ]

def test_validator_all_with_contains():
    validator = InvalidModifierCombinationsValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field|contains|all:
                - value1
                - value2
                - value3
        condition: sel
    """)
    assert validator.validate(rule) == [ ]

def test_validator_base64offset_without_contains_modifier():
    validator = InvalidModifierCombinationsValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field|base64offset: value
        condition: sel
    """)
    assert validator.validate(rule) == [
        Base64OffsetWithoutContainsModifierIssue(
            [ rule ],
            SigmaDetectionItem("field", [ SigmaBase64OffsetModifier ], [ "value" ])
        )
    ]

def test_validator_base64offset_after_contains_modifier():
    with pytest.raises(SigmaValueError, match="strings with wildcards"):
        rule = SigmaRule.from_yaml("""
        title: Test
        status: test
        logsource:
            category: test
        detection:
            sel:
                field|contains|base64offset: value
            condition: sel
        """)

def test_validator_base64offset_with_contains_modifier():
    validator = InvalidModifierCombinationsValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field|base64offset|contains: value
        condition: sel
    """)
    assert validator.validate(rule) == [ ]

def test_validator_multiple_modifier():
    validator = InvalidModifierCombinationsValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field|base64offset|base64offset|contains|contains: value
        condition: sel
    """)
    assert validator.validate(rule) == [
        ModifierAppliedMultipleIssue(
            [ rule ],
            SigmaDetectionItem("field", [ SigmaBase64OffsetModifier, SigmaBase64OffsetModifier, SigmaContainsModifier, SigmaContainsModifier ], [ "value" ]),
            { SigmaBase64OffsetModifier, SigmaContainsModifier }
        )
    ]

def test_validator_multiple_base64_modifier():
    validator = InvalidModifierCombinationsValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field|base64|base64: value
        condition: sel
    """)
    assert validator.validate(rule) == [ ]

def test_validator_invalid_attack_tags():
    validator = ATTACKTagValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field: value
        condition: sel
    tags:
        - attack.test1
        - attack.test2
    """)
    assert validator.validate(rule) == [
        InvalidATTACKTagIssue([ rule ], SigmaRuleTag.from_str("attack.test1")),
        InvalidATTACKTagIssue([ rule ], SigmaRuleTag.from_str("attack.test2")),
    ]

def test_validator_invalid_attack_tags():
    validator = ATTACKTagValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field: value
        condition: sel
    tags:
        - attack.test1
        - attack.test2
    """)
    assert validator.validate(rule) == [
        InvalidATTACKTagIssue([ rule ], SigmaRuleTag.from_str("attack.test1")),
        InvalidATTACKTagIssue([ rule ], SigmaRuleTag.from_str("attack.test2")),
    ]


def test_validator_invalid_attack_tags():
    validator = ATTACKTagValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field: value
        condition: sel
    tags:
        - attack.test1
        - attack.test2
    """)
    assert validator.validate(rule) == [
        InvalidATTACKTagIssue([ rule ], SigmaRuleTag.from_str("attack.test1")),
        InvalidATTACKTagIssue([ rule ], SigmaRuleTag.from_str("attack.test2")),
    ]

def test_validator_valid_attack_tags():
    validator = ATTACKTagValidator()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field: value
        condition: sel
    tags:
        - attack.command_and_control
        - attack.t1001.001
    """)
    assert validator.validate(rule) == [ ]

@pytest.mark.parametrize(
    "validator_class,tags,issue_tags", [
        (TLPv1TagValidator, [ "tlp.clear", "tlp.white" ], [ "tlp.clear" ]),
        (TLPv2TagValidator, [ "tlp.clear", "tlp.white" ], [ "tlp.white" ]),
        (TLPTagValidator, [ "tlp.clear", "tlp.white" ], [ ]),
        (TLPTagValidator, [ "tlp.clear", "tlp.white", "tlp.test" ], [ "tlp.test" ]),
    ],
    ids=[
        "TLPv1-invalid",
        "TLPv2-invalid",
        "TLP-valid",
        "TLP-invalid",
    ]
)
def test_validator_tlp_tags(validator_class, tags, issue_tags):
    validator = validator_class()
    rule = SigmaRule.from_yaml("""
    title: Test
    status: test
    logsource:
        category: test
    detection:
        sel:
            field: value
        condition: sel
    """)
    rule.tags = [
        SigmaRuleTag.from_str(tag)
        for tag in tags
    ]
    assert validator.validate(rule) == [
        InvalidTLPTagIssue( [ rule ], SigmaRuleTag.from_str(tag))
        for tag in issue_tags
    ]