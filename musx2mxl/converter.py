from io import BytesIO
from lxml.etree import Element, SubElement, parse, ElementTree, XMLSyntaxError
from musx2mxl.helper import calculate_mode_and_key_fifths, calculate_type_and_dots, calculate_step_alter_and_octave, \
    translate_clef_sign, translate_bar_style, replace_music_symbols, remove_styling_tags, translate_dynamics, \
    count_tuplet, translate_articualtion

ns = {"f": "http://www.makemusic.com/2012/finale"}
ns2 = {"m": "http://www.makemusic.com/2012/NotationMetadata"}
DIVISIONS = 4  # nb devisions per quarter note

VERBOSE = False

# Finale Bracket Styles
THICK_LINE = '1'
BRACKET_STRAIGHT_HOOKS = '2'
PIANO_BRACE = '3'
BRACKET_CURVED_HOOKS = '6'
DESK_BRACKET = '8'


def convert_from_stream(input_stream, metadata_stream, output_stream):
    """
    Convert data from an input stream and return the converted data as a bytes object.
    """
    tree = parse(input_stream)

    try:
        meta_tree = parse(metadata_stream)
    except XMLSyntaxError as e:
        # try to solve wrong encoding
        metadata_stream = BytesIO(metadata_stream.getvalue().decode("latin1").encode("utf-8"))
        meta_tree = parse(metadata_stream)

    output_tree = convert_tree(tree, meta_tree)
    output_tree.write(output_stream, pretty_print=True, encoding="UTF-8", xml_declaration=True)


def lookup_note_alter(root, entnum: str):
    noteAlters = root.xpath(f"/f:finale/f:details/f:noteAlter[@entnum = '{entnum}'][f:noteID]", namespaces=ns)
    noteAlter_map = {}
    for noteAlter in noteAlters:
        noteID = noteAlter.find("f:noteID", namespaces=ns).text
        enharmonic = noteAlter.find("f:enharmonic", namespaces=ns) is not None
        percent = noteAlter.find("f:percent", namespaces=ns) if noteAlter.find("f:percent",
                                                                               namespaces=ns) is not None else None
        noteAlter_map[noteID] = {"enharmonic": enharmonic, "percent": percent}
    return noteAlter_map


def lookup_meas_expressions(root, meas_spec_cmper: str):
    expressions = []
    measExprAssigns = root.xpath(f"/f:finale/f:others/f:measExprAssign[@cmper='{meas_spec_cmper}'][f:textExprID]",
                                 namespaces=ns)
    for measExprAssign in measExprAssigns:
        textExprID = measExprAssign.find("f:textExprID", namespaces=ns).text
        staffAssign = measExprAssign.find("f:staffAssign", namespaces=ns).text
        textExprDef = root.xpath(f"/f:finale/f:others/f:textExprDef[@cmper='{textExprID}']", namespaces=ns)[0]
        textIDKey = textExprDef.find("f:textIDKey", namespaces=ns).text
        categoryID = textExprDef.find("f:categoryID", namespaces=ns).text
        value = textExprDef.find("f:value", namespaces=ns).text if textExprDef.find("f:value",
                                                                                    namespaces=ns) is not None else None
        descStr = textExprDef.find("f:descStr", namespaces=ns).text if textExprDef.find("f:descStr",
                                                                                        namespaces=ns) is not None else None
        textBlock = root.find(f"f:others/f:textBlock[@cmper='{textIDKey}']", namespaces=ns)
        expression_text = None
        if textBlock is not None:
            markingsCategory = \
                root.xpath(f"/f:finale/f:others/f:markingsCategory[@cmper='{categoryID}']", namespaces=ns)[0]
            textID = textBlock.find("f:textID", namespaces=ns).text
            textTag = textBlock.find("f:textTag", namespaces=ns).text
            showShape = textBlock.find("f:textTag", namespaces=ns) is not None
            categoryType = markingsCategory.find("f:categoryType", namespaces=ns).text
            expression_text = root.find(f"f:texts/f:expression[@number='{textID}']", namespaces=ns).text if root.find(
                f"f:texts/f:expression[@number='{textID}']", namespaces=ns) is not None else None
        else:
            print(f'textBlock with cmper {textIDKey} not found.')

        if expression_text:
            # todo what if expression_text is not found
            expression = {
                "staffAssign": staffAssign,
                "value": value,
                "categoryType": categoryType,
                "textTag": textTag,
                "showShape": showShape,
                "descStr": descStr,
                "text": expression_text,
            }
            expressions.append(expression)
    return expressions


def lookup_meas_smart_shapes(root, meas_spec_cmper):
    smartShapeMeasMarks = root.xpath(f"/f:finale/f:others/f:smartShapeMeasMark[@cmper='{meas_spec_cmper}']",
                                     namespaces=ns)
    meas_smart_shapes = []
    for smartShapeMeasMark in smartShapeMeasMarks:
        shapeNum = smartShapeMeasMark.find('f:shapeNum', namespaces=ns).text
        smartShape = root.find(f"f:others/f:smartShape[@cmper = '{shapeNum}']", namespaces=ns)
        if smartShape is None:
            print(f'smartShape with cmper {shapeNum} not found')
        else:
            shapeType = smartShape.find("f:shapeType", namespaces=ns).text if smartShape.find("f:shapeType",
                                                                                              namespaces=ns) is not None else None
            startMeas = smartShape.find("f:startTermSeg/f:endPt/f:meas", namespaces=ns).text
            startInst = smartShape.find("f:startTermSeg/f:endPt/f:inst", namespaces=ns).text
            startEntry = smartShape.find("f:startTermSeg/f:endPt/f:entryNum", namespaces=ns).text if smartShape.find(
                "f:startTermSeg/f:endPt/f:entryNum", namespaces=ns) is not None else None
            endMeas = smartShape.find("f:endTermSeg/f:endPt/f:meas", namespaces=ns).text
            endEntry = smartShape.find("f:endTermSeg/f:endPt/f:entryNum", namespaces=ns).text if smartShape.find(
                "f:endTermSeg/f:endPt/f:entryNum", namespaces=ns) is not None else None
            endInst = smartShape.find("f:endTermSeg/f:endPt/f:inst", namespaces=ns).text
            meas_smart_shapes.append(
                {'shapeType': shapeType, 'startMeas': startMeas, 'startEntry': startEntry, 'startInst': startInst,
                 'endMeas': endMeas, 'endEntry': endEntry, 'endInst': endInst, })
    return meas_smart_shapes


def lookup_block_text(root, id):
    textBlock = root.xpath(f"/f:finale/f:others/f:textBlock[@cmper='{id}']", namespaces=ns)[0]
    textID = textBlock.find("f:textID", namespaces=ns).text
    text = root.xpath(f"/f:finale/f:texts/f:blockText[@number='{textID}']", namespaces=ns)[0].text
    if text:
        return replace_music_symbols(remove_styling_tags(text))
    else:
        print(f"blockText with number {textID} not found.")
        return ''


def lookup_staff_groups(root):
    # todo check multiStaffInstGroup and multiStaffGroupID
    staff_group_list = []
    staff_groups = root.xpath("/f:finale/f:details/f:staffGroup[not(@part)]", namespaces=ns)
    for staffGroup in staff_groups:
        startInst = staffGroup.find("f:startInst", namespaces=ns).text
        endInst = staffGroup.find("f:endInst", namespaces=ns).text
        startMeas = staffGroup.find("f:startMeas", namespaces=ns).text
        endMeas = staffGroup.find("f:endMeas", namespaces=ns).text
        fullID_ = staffGroup.find("f:fullID", namespaces=ns)
        abbrvID_ = staffGroup.find("f:abbrvID", namespaces=ns)
        fullName = lookup_block_text(root, fullID_.text) if fullID_ is not None else None
        abbrvName = lookup_block_text(root, abbrvID_.text) if abbrvID_ is not None else None
        bracket_id = staffGroup.find("f:bracket/f:id", namespaces=ns).text if staffGroup.find("f:bracket/f:id", namespaces=ns) is not None else None
        staff_group_list.append({'startInst': startInst, 'endInst': endInst, 'startMeas': startMeas, 'endMeas': endMeas,
                                 'fullName': fullName, 'abbrvName': abbrvName, 'bracket_id': bracket_id})
    if VERBOSE: print(f"staff_group_list: {staff_group_list}")
    return staff_group_list


def find_staff_group_name(param, staff_spec_cmper, staff_groups):
    names = []
    for staff_group in staff_groups:
        if int(staff_group["startInst"]) <= int(staff_spec_cmper) <= int(staff_group["endInst"]) and staff_group[
            param]:
            names.append(staff_group[param])
    return ' '.join(names) if names else None


def get_piano_brace_staff_group(staff_spec_cmper, staff_groups):
    for staff_group in staff_groups:
        if (staff_group["bracket_id"] == PIANO_BRACE and staff_group["startInst"] != staff_group["endInst"] and
                int(staff_group["startInst"]) <= int(staff_spec_cmper) <= int(staff_group["endInst"])):
            return staff_group
    return None


def convert_tree(tree, meta_tree):
    root = tree.getroot()
    score_partwise = Element("score-partwise", version="4.0", nsmap={None: "http://www.musicxml.org"})

    if meta_tree:
        meta_root = meta_tree.getroot()
        handle_meta_data(score_partwise, meta_root)
    part_list = SubElement(score_partwise, "part-list")

    timeSigDoAbrvCommon = len(
        root.xpath("/f:finale/f:options/f:timeSignatureOptions/f:timeSigDoAbrvCommon", namespaces=ns)) > 0
    timeSigDoAbrvCut = len(
        root.xpath("/f:finale/f:options/f:timeSignatureOptions/f:timeSigDoAbrvCut", namespaces=ns)) > 0

    staff_groups = lookup_staff_groups(root)

    staff_specs = root.xpath("/f:finale/f:others/f:staffSpec[@cmper != '32767']", namespaces=ns)
    i = 1
    part_ids = {}
    for staff_spec in staff_specs:
        staff_spec_cmper = staff_spec.get("cmper")
        fullName_ = staff_spec.find('f:fullName', namespaces=ns)
        abbrvName_ = staff_spec.find('f:abbrvName', namespaces=ns)
        if fullName_ is not None:
            fullName = lookup_block_text(root, fullName_.text)
        else:
            fullName = find_staff_group_name('fullName', staff_spec_cmper, staff_groups)
        if abbrvName_ is not None:
            abbrvName = lookup_block_text(root, abbrvName_.text)
        else:
            abbrvName = find_staff_group_name('abbrvName', staff_spec_cmper, staff_groups)

        piano_staff_group = get_piano_brace_staff_group(staff_spec_cmper, staff_groups)
        if piano_staff_group is None or piano_staff_group['startInst'] == staff_spec_cmper:
            part_id = f"P{i}"
            i += 1
            part_ids[staff_spec_cmper] = part_id
            score_part = SubElement(part_list, "score-part", id=part_id)
            if fullName:
                SubElement(score_part, "part-name").text = fullName
            if abbrvName:
                SubElement(score_part, "part-abbreviation").text = abbrvName

    handle_tempo = True  # todo how to handle tempo changes correctly

    for staff_spec in staff_specs:
        staff_spec_cmper = staff_spec.get("cmper")
        if staff_spec_cmper in part_ids:
            part = SubElement(score_partwise, "part", id=part_ids[staff_spec_cmper])

            piano_staff_group = get_piano_brace_staff_group(staff_spec_cmper, staff_groups)

            key_adjust = int(
                staff_spec.find('f:transposition/f:keysig/f:adjust', namespaces=ns).text) if staff_spec.find(
                'f:transposition/f:keysig/f:adjust', namespaces=ns) is not None else 0

            current_key = None
            current_beats = None
            current_divbeat = None
            current_clefID = None
            ending_cnt = 0  # todo how to find ending numbers correctly

            meas_specs = root.xpath("/f:finale/f:others/f:measSpec[not(@shared) and not(@part)]", namespaces=ns)
            nb_measures = len(meas_specs)
            for meas_idx, meas_spec in enumerate(meas_specs):
                meas_spec_cmper = meas_spec.get("cmper")
                if VERBOSE: print(f'Staff: {staff_spec_cmper} - Measure: {meas_spec_cmper}')
                measure = SubElement(part, "measure", number=meas_spec_cmper)
                beats = meas_spec.find("f:beats", namespaces=ns).text
                divbeat = meas_spec.find("f:divbeat", namespaces=ns).text
                key_ = meas_spec.find("f:keySig/f:key", namespaces=ns)
                barline_ = meas_spec.find("f:barline", namespaces=ns).text if meas_spec.find("f:barline",
                                                                                             namespaces=ns) is not None else 'normal'
                if meas_idx == nb_measures - 1:
                    barline_ = 'final'
                forRepBar = meas_spec.find("f:forRepBar", namespaces=ns) is not None
                bacRepBar = meas_spec.find("f:bacRepBar", namespaces=ns) is not None
                barEnding = meas_spec.find("f:barEnding", namespaces=ns) is not None
                hasSmartShape = meas_spec.find("f:hasSmartShape", namespaces=ns) is not None
                if hasSmartShape:
                    meas_smart_shapes = lookup_meas_smart_shapes(root, meas_spec_cmper)
                    if VERBOSE: print(f'Measure smart shapes: {meas_smart_shapes}')
                else:
                    meas_smart_shapes = []
                # todo: Check if inst is always referring to staff_spec_cmper
                for meas_smart_shape in meas_smart_shapes:
                    if meas_smart_shape['shapeType'] == 'cresc' and meas_smart_shape['startMeas'] == meas_spec_cmper and \
                            meas_smart_shape['startInst'] == staff_spec_cmper:
                        direction = SubElement(measure, "direction", placement='below')
                        direction_type = SubElement(direction, "direction-type")
                        SubElement(direction_type, "wedge", type="crescendo")
                    elif meas_smart_shape['shapeType'] == 'decresc' and meas_smart_shape[
                        'startMeas'] == meas_spec_cmper and \
                            meas_smart_shape['endInst'] == staff_spec_cmper:
                        direction = SubElement(measure, "direction", placement='below')
                        direction_type = SubElement(direction, "direction-type")
                        SubElement(direction_type, "wedge", type="diminuendo")

                leftBarline = meas_spec.find("f:leftBarline", namespaces=ns).text
                if key_ is None:
                    key = None
                else:
                    key = int(key_.text)

                attributes = None
                if (meas_idx == 0):
                    attributes = handle_devisions(measure)
                if key != current_key:
                    attributes = handle_key_change(measure, attributes, key, key_adjust)
                    current_key = key

                if beats != current_beats or divbeat != current_divbeat:
                    attributes = handle_time_change(measure, attributes, beats, divbeat, timeSigDoAbrvCommon,
                                                    timeSigDoAbrvCut)
                    current_beats = beats
                    current_divbeat = divbeat

                if forRepBar or barEnding:
                    left_barline = SubElement(measure, "barline", location='left')
                    if barEnding:
                        ending_cnt += 1
                        SubElement(left_barline, "ending", number=str(ending_cnt), type='start').text = f'{ending_cnt}.'
                    if forRepBar:
                        SubElement(left_barline, "bar-style").text = 'heavy-light'
                        SubElement(left_barline, "repeat", direction='forward')

                if piano_staff_group:
                    staff_id = 1
                    clefIDs = {}
                    prev = False
                    for staff_spec in staff_specs:
                        staff_spec_cmper = staff_spec.get("cmper")
                        if int(piano_staff_group["startInst"]) <= int(staff_spec_cmper) <= int(
                                piano_staff_group["endInst"]):
                            if prev:
                                backup = SubElement(measure, "backup")
                                # todo is duration correctly calculated? Always start from start measure?
                                SubElement(backup, "duration").text = str(
                                    (int(current_beats) * int(current_divbeat) * DIVISIONS) // 1024)
                            clefID, handle_tempo = process_gfholds(staff_spec_cmper, meas_spec_cmper, staff_id,
                                                                           measure, root, meas_spec,
                                                                           meas_smart_shapes, handle_tempo, barline_,
                                                                           bacRepBar, barEnding, ending_cnt,
                                                                           current_beats, current_divbeat, key,
                                                                           key_adjust)
                            clefIDs[staff_id] = clefID
                            staff_id += 1
                            prev = True
                    if clefIDs != current_clefID:
                        attributes = handle_mutli_staff_cleff_change(root, measure, attributes, clefIDs)
                        current_clefID = clefIDs
                else:
                    clefID, handle_tempo = process_gfholds(staff_spec_cmper, meas_spec_cmper, None, measure,
                                                                   root, meas_spec, meas_smart_shapes,
                                                                   handle_tempo, barline_, bacRepBar, barEnding,
                                                                   ending_cnt, current_beats, current_divbeat, key,
                                                                   key_adjust)
                    # todo handle clefListID =(mid-measure clef changes)
                    # todo use <hasExpr/> to determine show time_signature
                    # todo use <showClefFirstSystemOnly/> to determine show clef
                    if clefID != current_clefID:
                        attributes = handle_clef_change(root, measure, attributes, clefID)
                        current_clefID = clefID

    return ElementTree(score_partwise)


# default-x="616.935484" default-y="1511.049022" justify="center" valign="top" font-size="22"
def add_credit(score_partwise, page, credit_type, credit_words, default_x, default_y, justify, valign, font_size):
    credit = SubElement(score_partwise, "credit", page=str(page))
    credit_type_ = SubElement(credit, "credit-type")
    credit_type_.text = credit_type
    credit_words_ = SubElement(credit, "credit-words")
    credit_words_.set('default-x', str(default_x))
    credit_words_.set('default-y', str(default_y))
    credit_words_.set('justify', justify)
    credit_words_.set('valign', valign)
    credit_words_.set('font-size', str(font_size))
    credit_words_.text = credit_words


def handle_meta_data(score_partwise, meta_root):
    SubElement(score_partwise, "defautls")
    title = meta_root.xpath("/m:metadata/m:fileInfo/m:title", namespaces=ns2)[0] if meta_root.xpath(
        "/m:metadata/m:fileInfo/m:title", namespaces=ns2) else None
    if title is not None:
        add_credit(score_partwise, 1, 'title', title.text, 616.935484, 1511.049022, 'center', 'top', 22)
    subtitle = meta_root.xpath("/m:metadata/m:fileInfo/m:subtitle", namespaces=ns2)[0] if meta_root.xpath(
        "/m:metadata/m:fileInfo/m:subtitle", namespaces=ns2) else None
    if subtitle is not None:
        add_credit(score_partwise, 1, 'subtitle', subtitle.text, 616.935484, 1453.898908, 'center', 'top', 14)
    composer = meta_root.xpath("/m:metadata/m:fileInfo/m:composer", namespaces=ns2)[0] if meta_root.xpath(
        "/m:metadata/m:fileInfo/m:composer", namespaces=ns2) else None
    if composer is not None:
        add_credit(score_partwise, 1, 'composer', composer.text, 1148.145796, 1411.049022, 'right', 'bottom', 10)


def handle_devisions(measure):
    attributes = SubElement(measure, "attributes")
    divisions = SubElement(attributes, "divisions")
    divisions.text = str(DIVISIONS)

    return attributes

def lookup_clef_info(root, clefID:str):
    if clefID:
        clef_def = root.find(f"f:options/f:clefOptions/f:clefDef[@index = '{clefID}']", namespaces=ns)
        clef_char = clef_def.find('f:clefChar', namespaces=ns)
        clef_char_ = clef_char.text if clef_char is not None else None
        # todo what if shape instead of clef_char (example : TAB)
        sign, clef_octave_change = translate_clef_sign(clef_char_)
        clef_y_disp = clef_def.find('f:clefYDisp', namespaces=ns)
        clef_y_disp_ = int(clef_y_disp.text) if clef_y_disp is not None else 0
        line = str(5 + clef_y_disp_ // 2)
        return {'sign': sign, 'line': line, 'clef_octave_change': str(clef_octave_change)}
    else:
        return {'sign': 'G', 'line': '2', 'clef_octave_change': '0'}

def handle_mutli_staff_cleff_change(root, measure, attributes, clefIDs):
    if attributes is None:
        attributes = SubElement(measure, "attributes")
    for staff_id, clefID in clefIDs.items():
        clef_info = lookup_clef_info(root, clefID)
        clef = SubElement(attributes, "clef", number=str(staff_id))
        sign = SubElement(clef, "sign")
        sign.text = clef_info['sign']
        line = SubElement(clef, "line")
        line.text = clef_info['line']
        if clef_info['clef_octave_change'] != '0':
            clef_octave_change = SubElement(clef, "clef-octave-change").text = clef_info['clef_octave_change']

    return attributes

def handle_clef_change(root, measure, attributes, clefID):
    if attributes is None:
        attributes = SubElement(measure, "attributes")

    clef_info = lookup_clef_info(root, clefID)
    clef = SubElement(attributes, "clef")
    sign = SubElement(clef, "sign")
    sign.text = clef_info['sign']
    line = SubElement(clef, "line")
    line.text = clef_info['line']
    if clef_info['clef_octave_change'] != '0':
        clef_octave_change = SubElement(clef, "clef-octave-change")
        clef_octave_change.text = clef_info['clef_octave_change']

    return attributes


def handle_key_change(measure, attributes, key, key_adjust):
    mode, fifths = calculate_mode_and_key_fifths(key, key_adjust)
    if attributes is None:
        attributes = SubElement(measure, "attributes")
    key_ = SubElement(attributes, "key")
    SubElement(key_, "fifths").text = str(fifths)
    SubElement(key_, "mode").text = mode
    return attributes


def handle_time_change(measure, attributes, beats, divbeat, timeSigDoAbrvCommon: bool, timeSigDoAbrvCut: bool):
    if attributes is None:
        attributes = SubElement(measure, "attributes")
    time_ = SubElement(attributes, "time")
    beats_ = SubElement(time_, "beats")
    beats_type = SubElement(time_, "beat-type")
    if divbeat == '1536':
        beats_type.text = '8'
        beats_.text = str(int(beats) * 3)
    else:
        beats_.text = beats
        beats_type.text = str(4096 // int(divbeat))
        if beats == '4' and divbeat == '1024' and timeSigDoAbrvCommon:
            time_.set('symbol', 'common')
        if beats == '2' and divbeat == '2048' and timeSigDoAbrvCut:
            time_.set('symbol', 'cut')
    return attributes


def process_frame(root, measure, frameSpec_cmper, frame_num, staff_id, key, key_adjust):
    if staff_id is None:
        voice = frame_num
    else:
        voice = (staff_id - 1) * 4 + frame_num
    frameSpecs = root.xpath(f"/f:finale/f:others/f:frameSpec[@cmper = '{frameSpec_cmper}']", namespaces=ns)
    for frameSpec in frameSpecs:
        startEntry = frameSpec.find("f:startEntry", namespaces=ns)
        endEntry = frameSpec.find("f:endEntry", namespaces=ns)
        if (startEntry is not None) and (endEntry is not None):
            process_frame_entries(root, measure, startEntry.text, endEntry.text, staff_id, voice, key, key_adjust, [])


def process_frame_entries(root, measure, current_entnum, end_entnum, staff_id, voice, key, key_adjust,
                          tuplet_attributes):
    current_entry = root.xpath(f"/f:finale/f:entries/f:entry[@entnum = '{current_entnum}']", namespaces=ns)[
        0] if root.xpath(f"/f:finale/f:entries/f:entry[@entnum = '{current_entnum}']", namespaces=ns) else None
    if current_entry is None:
        return
    tuplet_attributes = process_entry(root, measure, current_entry, staff_id, voice, key, key_adjust, tuplet_attributes)

    if current_entnum != end_entnum:
        next_entnum = current_entry.get("next")
        if next_entnum:
            process_frame_entries(root, measure, next_entnum, end_entnum, staff_id, voice, key, key_adjust,
                                  tuplet_attributes)


def handleTupletStart(root, entry, notations, tuplet_attributes):
    entnum = entry.get("entnum")
    tupletDefs = root.xpath(f"/f:finale/f:details/f:tupletDef[@entnum = '{entnum}']", namespaces=ns)
    if len(tuplet_attributes) == 0:
        idx = 0
    else:
        idx = max([int(tuplet_attribute['number']) for tuplet_attribute in tuplet_attributes])

    for tupletDef in tupletDefs:
        idx += 1
        number = str(idx)
        attributes = {
            'symbolicNum': tupletDef.find("f:symbolicNum", namespaces=ns).text,
            'symbolicDur': tupletDef.find("f:symbolicDur", namespaces=ns).text,
            'refNum': tupletDef.find("f:refNum", namespaces=ns).text,
            'refDur': tupletDef.find("f:refDur", namespaces=ns).text,
            'count': 0,
            'number': number,
        }
        tuplet = SubElement(notations, 'tuplet', number=number, type='start')
        if idx > 1:
            actual_type, _ = calculate_type_and_dots(int(attributes['symbolicDur']))
            normal_type, _ = calculate_type_and_dots(int(attributes['refDur']))
            tuplet_actual = SubElement(tuplet, 'tuplet-actual')
            SubElement(tuplet_actual, 'tuplet-number').text = attributes['symbolicNum']
            SubElement(tuplet_actual, 'tuplet-type').text = actual_type
            tuplet_normal = SubElement(tuplet, 'tuplet-normal')
            SubElement(tuplet_normal, 'tuplet-number').text = attributes['refNum']
            SubElement(tuplet_normal, 'tuplet-type').text = normal_type

        tuplet_attributes.append(attributes)

def handleSmartShapeDetail(root, entry, notations):
    entnum = entry.get("entnum")
    smartShapeEntryMarks = root.xpath(f"/f:finale/f:details/f:smartShapeEntryMark[@entnum = '{entnum}']", namespaces=ns)
    for smartShapeEntryMark in smartShapeEntryMarks:
        shapeNum = smartShapeEntryMark.find('f:shapeNum', namespaces=ns).text
        smartShape = root.find(f"f:others/f:smartShape[@cmper = '{shapeNum}']", namespaces=ns)
        if smartShape is not None:
            shapeType = smartShape.find("f:shapeType", namespaces=ns).text if smartShape.find("f:shapeType",
                                                                                              namespaces=ns) is not None else None
            startEntry = smartShape.find("f:startTermSeg/f:endPt/f:entryNum", namespaces=ns).text
            endEntry = smartShape.find("f:startTermSeg/f:endPt/f:entryNum", namespaces=ns).text

            if shapeType == 'slurAuto' or shapeType == 'slurUp':
                slur_type = 'start' if startEntry == entnum else 'stop'
                SubElement(notations, 'slur', number='1', type=slur_type)
        else:
            print(f'Smart shape with cmper {shapeNum} not found.')


def lookup_artic_detail(root, entnum):
    articAssigns = root.xpath(f"/f:finale/f:details/f:articAssign[@entnum = '{entnum}'][f:articDef]", namespaces=ns)
    artic_details = []
    for articAssign in articAssigns:
        articDef_cmper = articAssign.find("f:articDef", namespaces=ns).text
        articDef = root.xpath(f"/f:finale/f:others/f:articDef[@cmper = '{articDef_cmper}']", namespaces=ns)[0]
        charMain = articDef.find("f:charMain", namespaces=ns).text
        charAlt = articDef.find("f:charAlt", namespaces=ns).text
        artic_details.append({'charMain': charMain, 'charAlt': charAlt})

    return artic_details


def add_rest_to_empty_measure(root, measure, meas_spec_cmper, staff_id):
    first_gfhold = root.find(f"f:details/f:gfhold[@cmper2 = '{meas_spec_cmper}'][f:frame1]", namespaces=ns)
    if first_gfhold is not None:
        frame = first_gfhold.find(f"f:frame1", namespaces=ns).text
        frameSpec = root.find(f"f:others/f:frameSpec[@cmper = '{frame}'][f:startEntry][f:endEntry]", namespaces=ns)
        start_entnum = frameSpec.find("f:startEntry", namespaces=ns).text
        end_entnum = frameSpec.find("f:endEntry", namespaces=ns).text
        current_entnum = None
        next_entnum = start_entnum
        dura = 0
        while current_entnum != end_entnum:
            entry = root.find(f"f:entries/f:entry[@entnum = '{next_entnum}']", namespaces=ns)
            current_entnum = next_entnum
            next_entnum = entry.get("next")
            dura += int(entry.find("f:dura", namespaces=ns).text)

        type_name, nb_dots = calculate_type_and_dots(dura)  # todo what if dura does not match type + dots
        note = SubElement(measure, "note")
        SubElement(note, "rest")
        SubElement(note, "duration").text = str((dura * DIVISIONS) // 1024)
        voice = (staff_id - 1) * 4 + 1 if staff_id is not None else 1
        SubElement(note, "voice").text = str(voice)
        SubElement(note, "type").text = type_name
        if staff_id:
            SubElement(note, "staff").text = str(staff_id)
        for _ in range(nb_dots):
            SubElement(note, "dot")


def process_gfholds(staff_spec_cmper, meas_spec_cmper, staff_id, measure, root, meas_spec,
                    meas_smart_shapes, handle_tempo, barline_, bacRepBar, barEnding, ending_cnt, current_beats,
                    current_divbeat, key, key_adjust):
    clefID = None
    gfholds = root.xpath(
        f"/f:finale/f:details/f:gfhold[@cmper1 = '{staff_spec_cmper}' and @cmper2 = '{meas_spec_cmper}']",
        namespaces=ns)
    if len(gfholds) == 0:
        first_clefID = root.find(f"f:details/f:gfhold[@cmper1 = '{staff_spec_cmper}']/f:clefID",
                                 namespaces=ns)
        clefID = first_clefID.text if first_clefID is not None else None
        add_rest_to_empty_measure(root, measure, meas_spec_cmper, staff_id)

    for gfhold in gfholds:
        if gfhold.find("f:clefID", namespaces=ns) is not None:
            clefID = gfhold.find("f:clefID", namespaces=ns).text
        if handle_tempo:
            beatsPerMinute = root.xpath(f"/f:finale/f:options/f:playbackOptions/f:beatsPerMinute",
                                        namespaces=ns)
            edusPerBeat = root.xpath(f"/f:finale/f:options/f:playbackOptions/f:edusPerBeat", namespaces=ns)
            if beatsPerMinute is not None and edusPerBeat is not None:
                direction = SubElement(measure, "direction", placement='above')
                direction_type = SubElement(direction, "direction-type")
                if staff_id:
                    SubElement(direction, "staff").text = str(staff_id)
                metronome = SubElement(direction_type, "metronome")
                type_name, nb_dots = calculate_type_and_dots(int(edusPerBeat[0].text))
                SubElement(metronome, "beat-unit").text = type_name
                SubElement(metronome, "per-minute").text = beatsPerMinute[0].text
            handle_tempo = False

        has_prev_frame = False
        for frame_num in range(1, 5):
            frame = gfhold.find(f"f:frame{frame_num}", namespaces=ns)
            if frame is not None:
                if has_prev_frame:
                    backup = SubElement(measure, "backup")
                    # todo is duration correctly calculated? Always start from start measure?
                    SubElement(backup, "duration").text = str(
                        (int(current_beats) * int(current_divbeat) * DIVISIONS) // 1024)
                frameSpec_cmper = frame.text
                process_frame(root, measure, frameSpec_cmper, frame_num, staff_id, key, key_adjust)
                has_prev_frame = True

    hasExpr = meas_spec.find("f:hasExpr", namespaces=ns) is not None
    if hasExpr:
        expressions = lookup_meas_expressions(root, meas_spec_cmper)
        for expression in expressions:
            if VERBOSE: print(f'Expression: {expression}')
            if expression['staffAssign'] == staff_spec_cmper:
                if expression['categoryType'] == 'misc':
                    # check if expression is recognizes as dynamics
                    dynamic_name = translate_dynamics(expression['text'])
                    if dynamic_name is not None:
                        expression['categoryType'] = 'dynamics'
                    else:
                        direction = SubElement(measure, "direction", placement='above')
                        direction_type = SubElement(direction, "direction-type")
                        if staff_id:
                            SubElement(direction, "staff").text = str(staff_id)
                        words = SubElement(direction_type, 'words')
                        words.text = remove_styling_tags(expression['text'])
                        words.set('font-style', 'italic')
                if expression['categoryType'] == 'dynamics':
                    dynamic_name = translate_dynamics(expression['text'])
                    if dynamic_name is not None:
                        direction = SubElement(measure, "direction", placement='below')
                        direction_type = SubElement(direction, "direction-type")
                        if staff_id:
                            SubElement(direction, "staff").text = str(staff_id)
                        dynamics = SubElement(direction_type, "dynamics")
                        SubElement(dynamics, dynamic_name)
                elif expression['categoryType'] == 'tempoAlts':
                    direction = SubElement(measure, "direction", placement='above')
                    direction_type = SubElement(direction, "direction-type")
                    if staff_id:
                        SubElement(direction, "staff").text = str(staff_id)
                    words = SubElement(direction_type, 'words')
                    words.text = remove_styling_tags(expression['text'])
                    words.set('font-style', 'italic')
                elif expression['categoryType'] == 'expressiveText':
                    direction = SubElement(measure, "direction", placement='bellow')
                    direction_type = SubElement(direction, "direction-type")
                    if staff_id:
                        SubElement(direction, "staff").text = str(staff_id)
                    words = SubElement(direction_type, 'words')
                    words.text = remove_styling_tags(expression['text'])
                    words.set('font-style', 'italic')
                elif expression['categoryType'] == 'techniqueText':
                    direction = SubElement(measure, "direction", placement='above')
                    direction_type = SubElement(direction, "direction-type")
                    if staff_id:
                        SubElement(direction, "staff").text = str(staff_id)
                    words = SubElement(direction_type, 'words')
                    words.text = remove_styling_tags(expression['text'])
                    words.set('font-style', 'italic')
                elif expression['categoryType'] == 'tempoMarks':
                    # todo: use instead of using element beatsPerMinute?
                    pass
                elif expression['categoryType'] == 'rehearsalMarks':
                    # todo: use instead of using elements forRepBar & bacRepBar?
                    pass

    barline = SubElement(measure, "barline", location="right")
    bar_style = SubElement(barline, "bar-style")
    bar_style.text = translate_bar_style(barline_, bacRepBar, barEnding)
    if barEnding:
        SubElement(barline, "ending", number=str(ending_cnt), type='stop').text = f'{ending_cnt}.'
    else:
        ending_cnt = 0
    if bacRepBar:
        SubElement(barline, "repeat", direction='backward', winged='none')

    for meas_smart_shape in meas_smart_shapes:
        if meas_smart_shape['shapeType'] == 'cresc' and meas_smart_shape['endMeas'] == meas_spec_cmper and \
                meas_smart_shape['startInst'] == staff_spec_cmper:
            direction = SubElement(measure, "direction", placement='below')
            direction_type = SubElement(direction, "direction-type")
            if staff_id:
                SubElement(direction, "staff").text = str(staff_id)
            SubElement(direction_type, "wedge", type="stop")
        elif meas_smart_shape['shapeType'] == 'decresc' and meas_smart_shape[
            'endMeas'] == meas_spec_cmper and \
                meas_smart_shape['endInst'] == staff_spec_cmper:
            direction = SubElement(measure, "direction", placement='below')
            direction_type = SubElement(direction, "direction-type")
            if staff_id:
                SubElement(direction, "staff").text = str(staff_id)
            SubElement(direction_type, "wedge", type="stop")

    return clefID, handle_tempo


def process_entry(root, measure, entry, staff_id, voice, key, key_adjust, tuplet_attributes):
    dura = int(entry.find("f:dura", namespaces=ns).text)
    is_note = entry.find("f:isNote", namespaces=ns) is not None
    noteDetail = entry.find("f:noteDetail", namespaces=ns) is not None
    articDetail = entry.find("f:articDetail", namespaces=ns) is not None
    if noteDetail:
        note_alter_map = lookup_note_alter(root, entry.get("entnum"))
        if VERBOSE: print(f'note_alter_map = {note_alter_map}')
    else:
        note_alter_map = {}

    if articDetail:
        artic_details = lookup_artic_detail(root, entry.get("entnum"))
        if VERBOSE: print(f'artic_detail_map = {artic_details}')
    else:
        artic_details = []

    # what is beam for?
    beam = entry.find("f:beam", namespaces=ns) is not None
    graceNote = entry.find("f:graceNote", namespaces=ns) is not None
    tupletStart = entry.find("f:tupletStart", namespaces=ns) is not None

    smartShapeDetail = entry.find("f:smartShapeDetail", namespaces=ns) is not None
    if is_note:
        # numNotes = int(entry.find("f:numNotes", namespaces=ns).text)
        notes = entry.xpath("f:note", namespaces=ns)
        for idx, note_ in enumerate(notes):
            note = SubElement(measure, "note")
            if idx > 0:
                SubElement(note, "chord")
            if graceNote:
                # todo add notation slur start and stop (target note) =  smartshape of type slurUp
                # todo determine when slash="yes"
                SubElement(note, "grace", slash="no")
            pitch = SubElement(note, "pitch")
            harm_lev = int(note_.find("f:harmLev", namespaces=ns).text)
            harm_alt = int(note_.find("f:harmAlt", namespaces=ns).text)
            enharmonic = note_alter_map[note_.get('id')]['enharmonic'] if note_.get('id') in note_alter_map else False
            step_value, alter_value, octave_value = calculate_step_alter_and_octave(harm_lev, harm_alt, key, key_adjust,
                                                                                    enharmonic)
            step = SubElement(pitch, "step")
            step.text = step_value
            octave = SubElement(pitch, "octave")
            octave.text = str(octave_value)
            if alter_value != 0:
                alter = SubElement(pitch, "alter")
                alter.text = str(alter_value)
            duration = SubElement(note, "duration")
            duration.text = str((dura * DIVISIONS) // 1024)

            tie_start = note_.find("f:tieStart", namespaces=ns)
            tie_end = note_.find("f:tieEnd", namespaces=ns)

            if tie_start is not None:
                SubElement(note, "tie", type='start')
            if tie_end is not None:
                SubElement(note, "tie", type='end')

            voice_elem = SubElement(note, "voice")
            voice_elem.text = str(voice)
            type_name, nb_dots = calculate_type_and_dots(dura)
            if type_name:  # type_name can be None if the dura is not supported
                type_elem = SubElement(note, "type")
                type_elem.text = type_name
                for _ in range(nb_dots):
                    SubElement(note, "dot")

            if staff_id:
                SubElement(note, "staff").text = str(staff_id)

            if idx == 0:
                notations = SubElement(note, "notations")
                if smartShapeDetail:
                    handleSmartShapeDetail(root, entry, notations)
                if tupletStart:
                    handleTupletStart(root, entry, notations, tuplet_attributes)
                if len(tuplet_attributes) > 0:
                    # todo handle symbolicDur != refDur
                    is_nested = len(tuplet_attributes) > 1
                    count_tuplet(tuplet_attributes, dura)
                    print(tuplet_attributes)
                    actual_notes = 1
                    normal_notes = 1
                    for attributes in tuplet_attributes:
                        actual_notes *= int(attributes['symbolicNum'])
                        normal_notes *= int(attributes['refNum'])
                        if attributes['count'] == int(attributes['symbolicNum']):
                            SubElement(notations, 'tuplet', number=attributes['number'], type='stop')
                            tuplet_attributes.remove(attributes)
                    time_modification = SubElement(note, "time-modification")
                    SubElement(time_modification, "actual-notes").text = str(actual_notes)
                    SubElement(time_modification, "normal-notes").text = str(normal_notes)
                    if is_nested :
                        normal_type, _ = calculate_type_and_dots(int(tuplet_attributes[0]['symbolicDur']))
                        SubElement(time_modification, "normal-type").text = normal_type

                if articDetail:
                    articulations = SubElement(notations, "articulations")
                    for art_detail in artic_details:
                        tag_name, type = translate_articualtion(art_detail['charMain'])
                        articulation = SubElement(articulations, tag_name)
                        if type:
                            articulation.set('type', type)

                # Remove empty notations element
                if len(notations.getchildren()) == 0:
                    note.remove(notations)


    else:
        note = SubElement(measure, "note")
        SubElement(note, "rest")
        duration = SubElement(note, "duration")
        duration.text = str((dura * DIVISIONS) // 1024)
        voice_elem = SubElement(note, "voice")
        voice_elem.text = str(voice)
        type_name, nb_dots = calculate_type_and_dots(dura)
        if type_name:  # type_name can be None if the dura is not supported
            type_elem = SubElement(note, "type")
            type_elem.text = type_name
            for _ in range(nb_dots):
                SubElement(note, "dot")
            if staff_id:
                SubElement(note, "staff").text = str(staff_id)
        notations = SubElement(note, "notations")
        if smartShapeDetail:
            handleSmartShapeDetail(root, entry, notations)
        if tupletStart:
            handleTupletStart(root, entry, notations, tuplet_attributes)
        if len(tuplet_attributes) > 0:
            # todo handle symbolicDur != refDur
            is_nested = len(tuplet_attributes) > 1
            count_tuplet(tuplet_attributes, dura)
            print(tuplet_attributes)
            actual_notes = 1
            normal_notes = 1
            for attributes in tuplet_attributes:
                actual_notes *= int(attributes['symbolicNum'])
                normal_notes *= int(attributes['refNum'])
                if attributes['count'] == int(attributes['symbolicNum']):
                    SubElement(notations, 'tuplet', number=attributes['number'], type='stop')
                    tuplet_attributes.remove(attributes)
            time_modification = SubElement(note, "time-modification")
            SubElement(time_modification, "actual-notes").text = str(actual_notes)
            SubElement(time_modification, "normal-notes").text = str(normal_notes)
            if is_nested:
                normal_type, _ = calculate_type_and_dots(int(tuplet_attributes[0]['symbolicDur']))
                SubElement(time_modification, "normal-type").text = normal_type

        # Remove empty notations element
        if len(notations.getchildren()) == 0:
            note.remove(notations)

    return tuplet_attributes
