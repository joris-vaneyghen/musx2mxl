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

ENGRAVER_CHAR_MAP_ARTICUALTIONS = {
    62: ('accent', None),
    94: ('strong-accent', 'up'),
    118: ('strong-accent', 'down'),
    46: ('staccato', None),
    95: ('tenuto', None),
    248: ('detached-legato', None),
    224: ('staccatissimo', None),
    -1: ('spiccato', None),# check correct char
    -2: ('scoop', None),
    103: ('plop', None), # check correct char
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
    214: ('percussion', 0),
    230: ('F', 1)
}


def calculate_mode_and_key_fifths(key: int, key_adjust: int) -> (str, int):
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

    key_fifths = key_fifths + key_adjust # key adjust for transposed instrument (ex F instr -> key_adjust = 1, Bb instr -> key_adjust = 2)
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


def calculate_step_alter_and_octave(harm_lev: int, harm_alt: int, key: int, key_adjust:int, enharmonic: bool) -> tuple[str, int, str]:
    mode, fifths = calculate_mode_and_key_fifths(key, key_adjust)
    notes = ('C', 'D', 'E', 'F', 'G', 'A', 'B')
    if mode == 'minor':
        harm_lev = harm_lev -2
    index = (harm_lev + (4 * fifths)) % 7
    step = notes[index]
    _, fifths_no_key_adjust = calculate_mode_and_key_fifths(key, 0)
    octave = 4 + (harm_lev + ((4 * fifths_no_key_adjust) % 7)  + ((4 * key_adjust) % 7) ) // 7
    alter = harm_alt + calculate_alter(step, fifths)
    if enharmonic:
        step, alter = calculate_enharmonic(step, alter)
    return step, alter, str(octave)


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


def do_tuplet_count(tuplet_attributes, dura):
    tuplet_attributes['count'] = tuplet_attributes['count'] + dura / int(tuplet_attributes['symbolicDur'])


def remove_styling_tags(text):
    cmds = [re.escape(cmd[1:]) for cmd in
            ["^font", "^fontid", "^Font", "^fontMus", "^fontTxt", "^fontNum", "^size", "^nfx"]
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

def translate_articualtion(charMain:str):
    if int(charMain) in ENGRAVER_CHAR_MAP_ARTICUALTIONS:
        return ENGRAVER_CHAR_MAP_ARTICUALTIONS[int(charMain)]
    else:
        return    'other-articulation', None

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


