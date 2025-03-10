import json
import importlib.resources
import re

SHARPS_AND_FLATS = ['F', 'C', 'G', 'D', 'A', 'E', 'B']

# Map of flags to note types, reversed to prioritize the most significant bit
FLAG_TO_TYPE = [
    (32768, 'maxima'), (16384, 'long'), (8192, 'breve'), (4096, 'whole'),
    (2048, 'half'), (1024, 'quarter'), (512, 'eighth'), (256, '16th'),
    (128, '32nd'), (64, '64th'), (32, '128th'), (16, '256th'),
    (8, '512th'), (4, '1024th')
]

BAR_LINE_TYPE_MAP = {
    'none': 'none',
    'normal': 'regular',
    'double': 'light-light',
    'final': 'light-heavy',
    'solid': 'heavy',
    'dash': 'dashed',
    'partial': 'tick',
}

ENGRAVER_CHAR_MAP_NOTE_TYPE = {
    'x': '16th',
    'e': 'eighth',
    'q': 'quarter',
    'h': 'half',
}

ENGRAVER_CHAR_MAP_ARTICUALTIONS = {
    62: ('accent', None),
    94: ('strong-accent', 'up'),
    118: ('strong-accent', 'down'),
    46: ('staccato', None),
    95: ('tenuto', None),
    248: ('detached-legato', None),
    224: ('staccatissimo', None),
    -1: ('spiccato', None),  # check correct char
    -2: ('scoop', None),
    103: ('plop', None),  # check correct char
    -5: ('doit', None),
    -4: ('falloff', None),
    44: ('breath-mark', None),
    34: ('caesura', None),
    -8: ('stress', None),
    -9: ('unstress', None),
    -10: ('soft-accent', None),
}

ENGRAVER_CHAR_MAP_DYNAMICS = {
    112: 'p',
    185: 'pp',
    184: 'ppp',
    175: 'pppp',
    102: 'f',
    196: 'ff',
    236: 'fff',
    235: 'ffff',
    80: 'mp',
    70: 'mf',
    83: 'sf',
    130: 'sfp',
    182: 'sfpp',
    234: 'fp',
    167: 'sfz',
    141: 'sffz',
    90: 'fz',
}

# mappging engraver char to clef sign and octave change
ENGRAVER_CHAR_MAP_CLEFS = {
    38: ('G', 0),
    63: ('F', 0),
    66: ('C', 0),
    86: ('G', -1),
    116: ('F', -1),
    160: ('G', 1),
    139: ('percussion', 0),
    # todo set setting defaults - appearance: <glyph type="percussion-clef">unpitchedPercussionClef1</glyph>
    214: ('percussion', 0),
    # todo set setting defaults - appearance: <glyph type="percussion-clef">unpitchedPercussionClef2</glyph>
    230: ('F', 1),
    57424: ('G', 0),
    57425: ('G', -2),
    57426: ('G', -1),
    57427: ('G', 1),
    57428: ('G', 2),
    57429: ('G', -1),
    57430: ('G', 0),
    57431: ('G', 0),
    57432: ('G', 0),
    57433: ('G', 0),
    57434: ('G', 0),
    57435: ('G', 0),
    57436: ('C', 0),
    57437: ('C', -1),
    57438: ('C', 0),
    57439: ('C', 0),
    57440: ('C', 0),
    57441: ('C', 0),
    57442: ('F', 0),
    57443: ('F', -2),
    57444: ('F', -1),
    57445: ('F', 1),
    57446: ('F', 2),
    57447: ('F', 0),
    57448: ('F', 0),
    57449: ('percussion', 0),
    57450: ('percussion', 0),
    57451: ('percussion', 0),
    57452: ('percussion', 0),
    61478: ('F', 0),
    61503: ('F', 0),
}

with importlib.resources.open_text("musx2mxl", "instruments.json") as json_file:
    INST_UUID_MAP = json.load(json_file)

# Define a dictionary where keys are chord kinds and values are regex patterns
CHORD_SUFFIX = {
    "69": {"kind": "major-sixth", "use-symbols": "yes", "parentheses-degrees": "no", "text": "",
           "degrees": [{"degree-value": 9, "degree-alter": 0, "degree-type": "add"}]},
    "6/9": {"kind": "major-sixth", "use-symbols": "yes", "parentheses-degrees": "no", "text": "",
            "degrees": [{"degree-value": 9, "degree-alter": 0, "degree-type": "add"}]},
}

# Define a common extension pattern
# EXTENSION_PATTERN = r"(?:\(|{|\[)?(?:alt|omit\d+|add\s?\d+|add\s?maj7|#\d+|\+\d+|\-\d+|b\d+|sus\d+)+(?:\)|}|\])?"
# Define the degree pattern separately
DEGREE_PATTERN = r"(?P<type>add|omit|alt|sus|maj7)?(?P<alter>[+\-b#])?(?P<value>[2-79]|11|13)?"

# Use the degree pattern inside the full degrees pattern
DEGREES_PATTERN = rf"(?P<parentheses_open>\(|{{|\[)?(?P<degrees>({DEGREE_PATTERN})+)(?P<parentheses_closed>\)|}}|\])?"

CHORD_PATTERNS = {
    "augmented-seventh": re.compile(fr"^(?P<kind>aug7|\+7|7\+)(?:{DEGREES_PATTERN})?$"),
    "augmented": re.compile(fr"^(?P<kind>aug|\+|\+5)(?:{DEGREES_PATTERN})?$"),
    "diminished-seventh": re.compile(fr"^(?P<kind>(?:'|`|dim|°|o)7)(?:{DEGREES_PATTERN})?$"),
    "diminished": re.compile(fr"^(?P<kind>'|`|dim|°|o)(?:{DEGREES_PATTERN})?$"),
    "half-diminished": re.compile(
        fr"^(?P<kind>(?:min|mi|m|-|−)7\(?[b\-−]?5\)?|ø7)(?:{DEGREES_PATTERN})?$"),
    "suspended-fourth": re.compile(fr"^(?P<kind>7?sus4?)(?:{DEGREES_PATTERN})?$"),
    "suspended-second": re.compile(fr"^(?P<kind>7?sus2)(?:{DEGREES_PATTERN})?$"),
    "dominant": re.compile(fr"^(?P<kind>7)(?:{DEGREES_PATTERN})?$"),
    "dominant-ninth": re.compile(fr"^(?P<kind>9)(?:{DEGREES_PATTERN})?$"),
    "dominant-11th": re.compile(fr"^(?P<kind>11)(?:{DEGREES_PATTERN})?$"),
    "dominant-13th": re.compile(fr"^(?P<kind>13)(?:{DEGREES_PATTERN})?$"),
    "major-sixth": re.compile(fr"^(?P<kind>(?:maj|ma|Δ)?6)(?:{DEGREES_PATTERN})?$"),
    "major-seventh": re.compile(fr"^(?P<kind>(?:maj|ma|Δ)7)(?:{DEGREES_PATTERN})?$"),
    "major-ninth": re.compile(fr"^(?P<kind>(?:maj|ma|Δ)9)(?:{DEGREES_PATTERN})?$"),
    "major-11th": re.compile(fr"^(?P<kind>(?:maj|ma|Δ)11)(?:{DEGREES_PATTERN})?$"),
    "major-13th": re.compile(fr"^(?P<kind>(?:maj|ma|Δ)13)(?:{DEGREES_PATTERN})?$"),
    "major-minor": re.compile(fr"^(?P<kind>min\(maj7\)|mi\(ma7\)|m\(ma7\)|-Δ7)(?:{DEGREES_PATTERN})?$"),
    "minor-sixth": re.compile(fr"^(?P<kind>(?:min|mi|m|-|−)6)(?:{DEGREES_PATTERN})?$"),
    "minor-seventh": re.compile(fr"^(?P<kind>(?:min|mi|m|-|−)7)(?:{DEGREES_PATTERN})?$"),
    "minor-ninth": re.compile(fr"^(?P<kind>(?:min|mi|m|-|−)9)(?:{DEGREES_PATTERN})?$"),
    "minor-11th": re.compile(fr"^(?P<kind>(?:min|mi|m|-|−)11)(?:{DEGREES_PATTERN})?$"),
    "minor-13th": re.compile(fr"^(?P<kind>(?:min|mi|m|-|−)13)(?:{DEGREES_PATTERN})?$"),
    "power": re.compile(fr"^(?P<kind>5|power)(?:{DEGREES_PATTERN})?$"),
    "major": re.compile(fr"^(?P<kind>maj|ma|Δ)?(?:{DEGREES_PATTERN})?$"),
    "minor": re.compile(fr"^(?P<kind>min|mi|m|-|−)(?:{DEGREES_PATTERN})?$"),
    "Italian": re.compile(fr"^(?P<kind>It6)(?:{DEGREES_PATTERN})?$"),
    "French": re.compile(fr"^(?P<kind>Fr6)(?:{DEGREES_PATTERN})?$"),
    "German": re.compile(fr"^(?P<kind>Gr6)(?:{DEGREES_PATTERN})?$"),
    "Tristan": re.compile(fr"^(?P<kind>Tristan)(?:{DEGREES_PATTERN})?$"),
}

DEFAULT_CHORD_SYMBOLS = {
    "augmented": "+",
    "augmented-seventh": "+7",
    "diminished": "°",
    "diminished-seventh": "°7",
    "half-diminished": "ø",
    "dominant": "7",
    "dominant-ninth": "9",
    "dominant-11th": "11",
    "dominant-13th": "13",
    "major": "Δ",
    "major-sixth": "Δ6",
    "major-seventh": "Δ7",
    "major-ninth": "Δ9",
    "major-11th": "Δ11",
    "major-13th": "Δ13",
    "major-minor": "-Δ7",
    "minor": "-",
    "minor-sixth": "-6",
    "minor-seventh": "-7",
    "minor-ninth": "-9",
    "minor-11th": "-11",
    "minor-13th": "-13",
    "suspended-fourth": "sus4",
    "suspended-second": "sus2",
    "power": "5",
    "Italian": "It6",
    "French": "Fr6",
    "German": "Gr6",
    "Tristan": "Tristan",
}


# Define a dictionary where keys are chord kinds and values are regex patterns


def translate_chord_suffix(chord_suffix):
    """Identify the kind of chord and its extensions."""
    chord_suffix = chord_suffix.strip() if chord_suffix else None
    if chord_suffix:
        if chord_suffix in CHORD_SUFFIX:
            return CHORD_SUFFIX[chord_suffix]
        else:
            for kind, pattern in CHORD_PATTERNS.items():
                match = pattern.match(chord_suffix)
                if match:
                    text = match.group("kind")
                    # todo handle extensions -> degrees
                    parentheses_degrees = "yes" if match.group("parentheses_open") and match.group("parentheses_closed") else "no"
                    degrees_text = match.group("degrees")
                    degrees = []
                    if degrees_text:
                        for degree_match in re.finditer(DEGREE_PATTERN, match.group("degrees")):
                            degree_alter = degree_match.group("alter")
                            if degree_alter in ['-','b']:
                                degree_alter =-1
                            elif degree_alter in ['+','#']:
                                degree_alter = 1
                            else:
                                degree_alter = 0
                            degree_type = degree_match.group("type")
                            if degree_type ==  'alt':
                                continue #todo
                            elif degree_type == 'sus':
                                # todo replace example C13 with degree 13
                                kind = "suspended-fourth"
                                text += 'sus'
                                parentheses_degrees = "no"
                                continue
                            elif degree_type == 'maj7':
                                # todo replace example min11 with degree 11
                                if kind.startswith('minor'):
                                    kind = "major-minor"
                                    text += "(maj7)"
                                    parentheses_degrees = "no"
                                if kind.startswith('diminished'):
                                    text += "(addmaj7)"
                                    parentheses_degrees = "no"
                                continue
                            elif degree_type ==  'omit':
                                degree_type = 'subtract'
                            else:
                                degree_type = 'add'
                            degree_value= degree_match.group("value")
                            if degree_value:
                                degrees.append({
                                    "degree-type": degree_type,
                                    "degree-alter": degree_alter,
                                    "degree-value": int(degree_value),
                                })

                    if text == DEFAULT_CHORD_SYMBOLS[kind]:
                        text = ""
                        use_symbols = "yes"
                    else:
                        use_symbols = "no"

                    return {"kind": kind, "use-symbols": use_symbols, "parentheses-degrees": parentheses_degrees, "text": text,
                            "degrees": degrees}
            print("could not translate suffix {}".format(chord_suffix))
            return {"kind": "other", "use-symbols": "no", "parentheses-degrees": "no", "text": chord_suffix,
                    "degrees": []}
    else:
        return {"kind": "major", "use-symbols": "no", "parentheses-degrees": "no", "text": "", "degrees": []}


def calculate_mode_and_key_fifths(key: int, transp_key_adjust) -> (str, int):
    # when key = None -> C maj
    # when key = 1 ... 7 -> G maj ... C# maj
    # when key = 255 ... 249 -> F maj ... Cb maj
    # when key = 256 -> A min
    # when key = 257 ... 263 -> E min ... A# min
    # when key = 511 ... 505 -> D min ... Ab min

    mode = 'major' if key is None or key < 256 else 'minor'
    if key is None:
        key_fifths = 0
    elif key > 384:
        key_fifths = key - 512
    elif key > 128:
        key_fifths = key - 256
    else:
        key_fifths = key

    key_fifths = key_fifths + transp_key_adjust  # key adjust for transposed instrument (ex F instr -> key_adjust = 1, Bb instr -> key_adjust = 2)
    if key_fifths > 7:
        key_fifths = key_fifths - 12
    if key_fifths < -7:
        key_fifths = key_fifths + 12

    return mode, key_fifths


def calculate_alter(step: str, key_fifths: int) -> int:
    if key_fifths == 0:
        return 0
    elif key_fifths > 0:
        return 1 if step in SHARPS_AND_FLATS[:key_fifths] else 0
    else:
        return -1 if step in SHARPS_AND_FLATS[7 + key_fifths:] else 0


def calculate_enharmonic(step, alter):
    """
    Given a note specified by a letter (step) and an accidental (alter),
    return an enharmonic equivalent note with a different letter name
    that represents the same pitch.

    Parameters:
        step (str): one of 'C', 'D', 'E', 'F', 'G', 'A', 'B'
        alter (int): number of sharps (if positive) or flats (if negative)

    Returns:
        (new_step, new_alter): a tuple where new_step is a note letter (different
        from step if possible) and new_alter is an integer (typically –1, 0, or 1)
        such that the note new_step with accidental new_alter is enharmonically
        equivalent to the input.

    Examples:
        calculate_enharmonic('F', -1) returns ('E', 0)
        calculate_enharmonic('G', 1)  returns ('A', -1)
        calculate_enharmonic('D', -2) returns ('C', 0)
    """
    # Natural note values in semitones (starting at C=0)
    base = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}

    # Compute the pitch (in semitones mod 12) for the given note.
    p = (base[step] + alter) % 12

    # List of natural note names
    notes = ['C', 'D', 'E', 'F', 'G', 'A', 'B']

    best_candidate = None
    best_acc = None
    # Try all note letters except the original one.
    for n in notes:
        if n == step:
            continue
        # Calculate the accidental needed so that (n, candidate_alter) has pitch p.
        # We adjust the difference so that it is as close to 0 as possible.
        diff = p - base[n]
        diff = ((diff + 6) % 12) - 6  # This yields a value in the range -6 to 5.
        # Pick the candidate with the smallest absolute accidental.
        if best_candidate is None or abs(diff) < abs(best_acc):
            best_candidate = n
            best_acc = diff

    return best_candidate, best_acc


def calculate_step_alter_and_octave(harm_lev: int, harm_alt: int, key: int, transp_key_adjust: int,
                                    transp_interval: int, enharmonic: bool) -> tuple[
    str, int, str]:
    mode, fifths = calculate_mode_and_key_fifths(key, transp_key_adjust)
    notes = ('C', 'D', 'E', 'F', 'G', 'A', 'B')
    if mode == 'minor':
        harm_lev = harm_lev - 2
    index = (harm_lev + (4 * fifths)) % 7
    step = notes[index]
    _, fifths_no_key_adjust = calculate_mode_and_key_fifths(key, 0)
    octave = 4 + (harm_lev + ((4 * fifths_no_key_adjust) % 7) + transp_interval) // 7
    if not 0 <= octave <= 9:
        print(f'Octave out of range: {octave}')
        octave = max(0, min(octave, 9))
    alter = harm_alt + calculate_alter(step, fifths)
    if enharmonic:
        step, alter = calculate_enharmonic(step, alter)
    return step, alter, str(octave)


def translate_tempo_marks(text: str):
    # todo translate dots, ties
    text_without_tags = remove_styling_tags(text)

    pattern = re.compile(r"(.*?\s+)?([({]\s*)?(m\s+)?([xeqh])([d|.])?\s*=\s*(c[a.]{0,2}\s+)?(\d+)(\s*[)}])?(\s+.*)?")
    match = pattern.match(text_without_tags)

    if match:
        prefix = match.group(1).strip() if match.group(1) else None
        has_bracket_open = match.group(2) is not None
        has_mm = match.group(3) is not None
        note = match.group(4)
        has_dot = match.group(5) is not None
        has_ca = match.group(6) is not None
        per_minute = match.group(7)
        has_bracket_closed = match.group(8) is not None
        postfix = match.group(9).strip() if match.group(9) else None

        words = prefix
        if postfix:
            words = words + ' ' + postfix
        if has_mm:
            words += ' M. M.'
        beat_unit = ENGRAVER_CHAR_MAP_NOTE_TYPE[note]
        if has_ca:
            per_minute = 'c. ' + per_minute
        parentheses = 'yes' if has_bracket_open and has_bracket_closed else 'no'
        return words, beat_unit, has_dot, per_minute, parentheses

    else:
        if '=' in text_without_tags:
            print('Could not parse tempo markings : {}'.format(text))
        return text_without_tags, None, False, None, None


def calculate_type_and_dots(dura: int) -> tuple[str, int]:
    """
    Extracts the type of note (e.g., quarter, eighth) and the number of augmentation dots.

    Parameters:
        dura (int): The duration represented as an integer. The most significant bit determines the note type,
                    and additional set bits to the right represent augmentation dots.

    Returns:
        tuple: A tuple containing the note type (str) and the number of dots (int)
    """
    note_type = None
    num_dots = 0
    for flag, type_name in FLAG_TO_TYPE:
        if dura & flag:
            if not note_type:
                note_type = type_name
            else:
                num_dots += 1
        elif note_type:
            break

    return note_type, num_dots


def translate_instrument(instUuid: str):
    if instUuid in INST_UUID_MAP:
        return INST_UUID_MAP[instUuid]['name'], INST_UUID_MAP[instUuid]['sound_id']
    else:
        print('instrument not found {}'.format(instUuid))
        return None, None


# todo can font be not Engraver?
def translate_clef_sign(clef_char: str) -> tuple[str, int]:
    if clef_char is not None and int(clef_char) in ENGRAVER_CHAR_MAP_CLEFS:
        return ENGRAVER_CHAR_MAP_CLEFS[int(clef_char)]
    else:
        print('Unknown clef char:', clef_char)
        sign = 'G'
        clef_octave_change = 0
    return sign, clef_octave_change


def translate_bar_style(bar_line_type: str, bacRepBar: bool, barEnding: bool) -> str:
    if bacRepBar or barEnding:
        return 'light-heavy'
    elif bar_line_type in BAR_LINE_TYPE_MAP:
        return BAR_LINE_TYPE_MAP[bar_line_type]
    else:
        return 'regular'


def count_tuplet(tuplet_attributes, dura):
    refactor = 1  # refactor for nested tuples
    for attributes in reversed(tuplet_attributes):
        attributes['count'] = attributes['count'] + refactor * dura / int(attributes['symbolicDur'])
        refactor *= int(attributes['refNum']) / int(attributes['symbolicNum'])


def remove_styling_tags(text):
    cmds = [re.escape(cmd[1:]) for cmd in
            ["^font", "^fontid", "^Font", "^fontMus", "^fontTxt", "^fontNum", "^size", "^nfx", "^baseline"]
            ]
    pattern = r"\^(?:" + "|".join(cmds) + r")\([^)]*\)"
    # Remove all occurrences of the pattern
    return re.sub(pattern, "", text).strip()


def replace_music_symbols(text):
    replacements = {
        r"\^flat\(\)": "\u266D",  # ♭
        r"\^sharp\(\)": "\u266F",  # ♯
        r"\^natural\(\)": "\u266E"  # ♮
    }

    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)

    return text


def translate_dynamics(text):
    text = remove_styling_tags(text)
    if len(text) == 1 and ord(text) in ENGRAVER_CHAR_MAP_DYNAMICS:
        return ENGRAVER_CHAR_MAP_DYNAMICS[ord(text)]
    else:
        return None


def translate_articualtion(charMain: str):
    if int(charMain) in ENGRAVER_CHAR_MAP_ARTICUALTIONS:
        return ENGRAVER_CHAR_MAP_ARTICUALTIONS[int(charMain)]
    else:
        return 'other-articulation', None


def translate_chord_step(key, transp_key_adjust, rootScaleNum, rootAlter):
    harm_lev = int(rootScaleNum) if rootScaleNum is not None else 0
    harm_alt = int(rootAlter) if rootAlter is not None else 0
    step, alter, _ = calculate_step_alter_and_octave(harm_lev, harm_alt, key, transp_key_adjust, 0, False)
    return step, alter


def calculate_transpose(interval: int):
    # translate diatonic interval (concert pitch to instrument pitch) to MusicXML transpose (instrument pitch to concert pitch)
    if interval < 0:
        is_transpose_up = True
        interval *= -1
    else:
        is_transpose_up = False

    octave_change = interval // 7
    diatonic = interval % 7
    if diatonic > 2:
        # compensate E->F semitone
        chromatic = diatonic * 2 - 1
    else:
        chromatic = diatonic * 2

    if is_transpose_up:
        return diatonic, chromatic, octave_change
    else:
        return -diatonic, -chromatic, -octave_change


def reorder_children(parent, element_order):
    """
    Reorders the children of the given parent element based on element_order.

    :param parent: lxml.etree.Element, the parent XML element
    :param element_order: list of str, the desired order of child element names
    """
    children_map = {child.tag: [] for child in parent}

    # Group children by tag
    for child in parent:
        children_map[child.tag].append(child)

    # Remove existing children
    parent.clear()

    # Append children in the specified order
    for tag in element_order:
        if tag in children_map:
            for elem in children_map[tag]:
                parent.append(elem)

    # Append any remaining elements that were not in element_order
    for tag, elems in children_map.items():
        if tag not in element_order:
            for elem in elems:
                parent.append(elem)


def find_nth_syllabic(lyrics: str, n: int) -> (str, str):
    # todo handle elision
    lyrics = remove_styling_tags(lyrics)
    lyrics = lyrics.replace('_ ', '_').replace('_', '_ ')  # normalize extend:'_abc' and '_ abc' to '_ abc'
    words = lyrics.split()
    syllabics = []

    for word in words:
        parts = word.split('-')
        for i, part in enumerate(parts):
            if part:
                extend = part.endswith('_')
                part = part.rstrip('_')  # Remove the extend character
                if len(parts) == 1:
                    syllabics.append((part, "single", extend))
                elif i == 0:
                    syllabics.append((part, "begin", extend))
                elif i == len(parts) - 1:
                    syllabics.append((part, "end", extend))
                else:
                    syllabics.append((part, "middle", extend))

    if 1 <= n <= len(syllabics):
        return syllabics[n - 1]
    else:
        print(f"No {n}th syllabic found for {lyrics}")
        return "???", "single", False


if __name__ == '__main__':
    dura = 1024 + 512 + 128
    print(calculate_type_and_dots(dura))
    # Test examples:
    print(calculate_enharmonic('F', -1))  # Expected output: ('E', 0) because F flat = E natural
    print(calculate_enharmonic('E', 0))  # Expected output: ('F', -1) because E natural = F flat
    print(calculate_enharmonic('G', 1))  # Expected output: ('A', -1) because G sharp = A flat
    print(calculate_enharmonic('D', -2))  # Expected output: ('C', 0) because D double flat = C natural
    print(calculate_enharmonic('C', -1))  # Expected output: ('B', 0) because C  flat = B natural

    # Example usage
    input_text = "This is a ^flat() note and this is a ^sharp() note, and this one is ^natural()."
    output_text = replace_music_symbols(input_text)
    print(output_text)
    print(calculate_transpose(1))

    print(translate_tempo_marks('^fontMus(EngraverTextT,8191)^size(12)^nfx(0)h. = q'))
