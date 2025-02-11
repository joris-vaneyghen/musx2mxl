from os import MFD_ALLOW_SEALING

from lxml.etree import Element, SubElement, parse, ElementTree

from musx2mxl.helper import calculate_mode_and_key_fifths, calculate_type_and_dots, calculate_step_alter_and_octave, \
    translate_clef_sign, translate_bar_style, replace_music_symbols, remove_styling_tags, translate_dynamics, \
    do_tuplet_count, translate_articualtion

ns = {"f": "http://www.makemusic.com/2012/finale"}
ns2 = {"m": "http://www.makemusic.com/2012/NotationMetadata"}
DIVISIONS = 2  # nb devisions per quarter note

VERBOSE = False

def convert_from_stream(input_stream, metadata_stream, output_stream):
    """
    Convert data from an input stream and return the converted data as a bytes object.
    """
    tree = parse(input_stream)
    meta_tree = parse(metadata_stream)
    output_tree = convert_tree(tree, meta_tree)
    output_tree.write(output_stream, pretty_print=True, encoding="UTF-8", xml_declaration=True)


def lookup_note_alter(root, entnum: str):
    noteAlters = root.xpath(f"/f:finale/f:details/f:noteAlter[@entnum = '{entnum}']", namespaces=ns)
    noteAlter_map = {}
    for noteAlter in noteAlters:
        noteID = noteAlter.find("f:noteID", namespaces=ns).text
        enharmonic = noteAlter.find("f:enharmonic", namespaces=ns) is not None
        percent = noteAlter.find("f:percent", namespaces=ns).text
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
        textBlock = root.xpath(f"/f:finale/f:others/f:textBlock[@cmper='{textIDKey}']", namespaces=ns)[0]
        markingsCategory = root.xpath(f"/f:finale/f:others/f:markingsCategory[@cmper='{categoryID}']", namespaces=ns)[0]
        textID = textBlock.find("f:textID", namespaces=ns).text
        textTag = textBlock.find("f:textTag", namespaces=ns).text
        showShape = textBlock.find("f:textTag", namespaces=ns) is not None
        categoryType = markingsCategory.find("f:categoryType", namespaces=ns).text
        expression_text = root.find(f"f:texts/f:expression[@number='{textID}']", namespaces=ns).text
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
        smartShape = root.xpath(f"/f:finale/f:others/f:smartShape[@cmper = '{shapeNum}']", namespaces=ns)[0]
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
    return replace_music_symbols(remove_styling_tags(text))


def convert_tree(tree, meta_tree):
    root = tree.getroot()
    meta_root = meta_tree.getroot()
    score_partwise = Element("score-partwise", version="4.0", nsmap={None: "http://www.musicxml.org"})
    handle_meta_data(score_partwise, meta_root)
    part_list = SubElement(score_partwise, "part-list")

    timeSigDoAbrvCommon = len(
        root.xpath("/f:finale/f:options/f:timeSignatureOptions/f:timeSigDoAbrvCommon", namespaces=ns)) > 0
    timeSigDoAbrvCut = len(
        root.xpath("/f:finale/f:options/f:timeSignatureOptions/f:timeSigDoAbrvCut", namespaces=ns)) > 0

    staff_specs = root.xpath("/f:finale/f:others/f:staffSpec[@cmper != '32767']", namespaces=ns)
    for i, staff_spec in enumerate(staff_specs):
        fullName_ = staff_spec.find('f:fullName', namespaces=ns)
        abbrvName_ = staff_spec.find('f:abbrvName', namespaces=ns)
        fullName = lookup_block_text(root, fullName_.text) if fullName_ is not None else None
        abbrvName = lookup_block_text(root, abbrvName_.text) if abbrvName_ is not None else None

        score_part = SubElement(part_list, "score-part", id=f"P{i + 1}")
        if fullName:
            SubElement(score_part, "part-name").text = fullName
        if abbrvName:
            SubElement(score_part, "part-abbreviation").text = abbrvName

    handle_tempo = True  # todo how to handle tempo changes correctly

    for i, staff_spec in enumerate(staff_specs):
        part = SubElement(score_partwise, "part", id=f"P{i + 1}")
        staff_spec_cmper = staff_spec.get("cmper")
        key_adjust = int(staff_spec.find('f:transposition/f:keysig/f:adjust', namespaces=ns).text) if staff_spec.find(
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
            if VERBOSE: print(f'Measure: {meas_spec_cmper}')
            measure = SubElement(part, "measure", number=meas_spec_cmper)
            beats = meas_spec.find("f:beats", namespaces=ns).text
            divbeat = meas_spec.find("f:divbeat", namespaces=ns).text
            key_ = meas_spec.find("f:keySig/f:key", namespaces=ns)
            barline_ = meas_spec.find("f:barline", namespaces=ns).text
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
                elif meas_smart_shape['shapeType'] == 'decresc' and meas_smart_shape['startMeas'] == meas_spec_cmper and \
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

            gfholds = root.xpath(
                f"/f:finale/f:details/f:gfhold[@cmper1 = '{staff_spec_cmper}' and @cmper2 = '{meas_spec_cmper}']",
                namespaces=ns)
            if len(gfholds) == 0:
                first_clefID = root.find(f"f:details/f:gfhold[@cmper1 = '{staff_spec_cmper}']/f:clefID", namespaces=ns)
                clefID = first_clefID.text if first_clefID is not None else None
                if clefID != current_clefID:
                    attributes = handle_cleff_change(root, measure, attributes, clefID)
                    current_clefID = clefID
                add_rest_to_empty_measure(root, measure, meas_spec_cmper)

            for gfhold in gfholds:
                clefID = gfhold.find("f:clefID", namespaces=ns).text
                # todo use <hasExpr/> to determine show time_signature
                # todo use <showClefFirstSystemOnly/> to determine show clef
                if clefID != current_clefID:
                    attributes = handle_cleff_change(root, measure, attributes, clefID)
                    current_clefID = clefID

                if handle_tempo:
                    beatsPerMinute = root.xpath(f"/f:finale/f:options/f:playbackOptions/f:beatsPerMinute",
                                                namespaces=ns)
                    edusPerBeat = root.xpath(f"/f:finale/f:options/f:playbackOptions/f:edusPerBeat", namespaces=ns)
                    if beatsPerMinute is not None and edusPerBeat is not None:
                        direction = SubElement(measure, "direction", placement='above')
                        direction_type = SubElement(direction, "direction-type")
                        metronome = SubElement(direction_type, "metronome")
                        type_name, nb_dots = calculate_type_and_dots(int(edusPerBeat[0].text))
                        SubElement(metronome, "beat-unit").text = type_name
                        SubElement(metronome, "per-minute").text = beatsPerMinute[0].text
                    handle_tempo = False

                for frame_num in range(1, 5):
                    frame = gfhold.find(f"f:frame{frame_num}", namespaces=ns)
                    if frame is not None:
                        frameSpec_cmper = frame.text
                        process_frame(root, measure, frameSpec_cmper, frame_num, key, key_adjust)

            hasExpr = meas_spec.find("f:hasExpr", namespaces=ns) is not None
            if hasExpr:
                expressions = lookup_meas_expressions(root, meas_spec_cmper)
                for expression in expressions:
                    if VERBOSE: print(f'Expression: {expression}')
                    if expression['staffAssign'] == staff_spec_cmper:
                        if expression['categoryType'] == 'dynamics':
                            dynamic_name = translate_dynamics(expression['text'])
                            if dynamic_name is not None:
                                direction = SubElement(measure, "direction", placement='below')
                                direction_type = SubElement(direction, "direction-type")
                                dynamics = SubElement(direction_type, "dynamics")
                                SubElement(dynamics, dynamic_name)
                        elif expression['categoryType'] == 'tempoAlts':
                            direction = SubElement(measure, "direction", placement='above')
                            direction_type = SubElement(direction, "direction-type")
                            words = SubElement(direction_type, 'words')
                            words.text = remove_styling_tags(expression['text'])
                            words.set('font-style', 'italic')
                        elif expression['categoryType'] == 'expressiveText':
                            direction = SubElement(measure, "direction", placement='bellow')
                            direction_type = SubElement(direction, "direction-type")
                            words = SubElement(direction_type, 'words')
                            words.text = remove_styling_tags(expression['text'])
                            words.set('font-style', 'italic')
                        elif expression['categoryType'] == 'techniqueText':
                            direction = SubElement(measure, "direction", placement='above')
                            direction_type = SubElement(direction, "direction-type")
                            words = SubElement(direction_type, 'words')
                            words.text = remove_styling_tags(expression['text'])
                            words.set('font-style', 'italic')
                        elif expression['categoryType'] == 'tempoMarks':
                            # todo: use instead of using element beatsPerMinute?
                            pass
                        elif expression['categoryType'] == 'rehearsalMarks':
                            # todo: use instead of using elements forRepBar & bacRepBar?
                            pass
                        elif expression['categoryType'] == 'misc':
                            direction = SubElement(measure, "direction", placement='above')
                            direction_type = SubElement(direction, "direction-type")
                            words = SubElement(direction_type, 'words')
                            words.text = remove_styling_tags(expression['text'])
                            words.set('font-style', 'italic')

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
                    SubElement(direction_type, "wedge", type="stop")
                elif meas_smart_shape['shapeType'] == 'decresc' and meas_smart_shape['endMeas'] == meas_spec_cmper and \
                        meas_smart_shape['endInst'] == staff_spec_cmper:
                    direction = SubElement(measure, "direction", placement='below')
                    direction_type = SubElement(direction, "direction-type")
                    SubElement(direction_type, "wedge", type="stop")

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


def handle_cleff_change(root, measure, attributes, clefID):
    if attributes is None:
        attributes = SubElement(measure, "attributes")

    clef_def = root.xpath(f"/f:finale/f:options/f:clefOptions/f:clefDef[@index = '{clefID}']", namespaces=ns)
    clef_char = clef_def[0].find('f:clefChar', namespaces=ns)
    clef_char_ = clef_char.text if clef_char is not None else None
    sign_, clef_octave_change_ = translate_clef_sign(clef_char_)
    clef_y_disp = clef_def[0].find('f:clefYDisp', namespaces=ns)
    clef_y_disp_ = int(clef_y_disp.text) if clef_y_disp is not None else 0
    clef = SubElement(attributes, "clef")
    sign = SubElement(clef, "sign")
    sign.text = sign_
    line = SubElement(clef, "line")
    line.text = str(5 + clef_y_disp_ // 2)
    if clef_octave_change_ != 0:
        clef_octave_change = SubElement(clef, "clef-octave-change")
        clef_octave_change.text = str(clef_octave_change_)

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
    beats_.text = beats
    beats_type = SubElement(time_, "beat-type")
    beats_type.text = str(int(divbeat) // 256)
    if beats == '4' and divbeat == '1024' and timeSigDoAbrvCommon:
        time_.set('symbol', 'common')
    if beats == '2' and divbeat == '2048' and timeSigDoAbrvCut:
        time_.set('symbol', 'cut')
    return attributes


def process_frame(root, measure, frameSpec_cmper, voice, key, key_adjust):
    frameSpecs = root.xpath(f"/f:finale/f:others/f:frameSpec[@cmper = '{frameSpec_cmper}']", namespaces=ns)
    for frameSpec in frameSpecs:
        startEntry = frameSpec.find("f:startEntry", namespaces=ns)
        endEntry = frameSpec.find("f:endEntry", namespaces=ns)
        if (startEntry is not None) and (endEntry is not None):
            process_frame_entries(root, measure, startEntry.text, endEntry.text, voice, key, key_adjust, None)


def process_frame_entries(root, measure, current_entnum, end_entnum, voice, key, key_adjust, tuplet_attributes):
    current_entry = root.xpath(f"/f:finale/f:entries/f:entry[@entnum = '{current_entnum}']", namespaces=ns)[
        0] if root.xpath(f"/f:finale/f:entries/f:entry[@entnum = '{current_entnum}']", namespaces=ns) else None
    if current_entry is None:
        return
    tuplet_attributes = process_entry(root, measure, current_entry, voice, key, key_adjust, tuplet_attributes)

    if current_entnum != end_entnum:
        next_entnum = current_entry.get("next")
        if next_entnum:
            process_frame_entries(root, measure, next_entnum, end_entnum, voice, key, key_adjust, tuplet_attributes)


def handleTupletStart(root, entry, notations):
    entnum = entry.get("entnum")
    tupletDefs = root.xpath(f"/f:finale/f:details/f:tupletDef[@entnum = '{entnum}']", namespaces=ns)
    for idx, tupletDef in enumerate(tupletDefs):
        number = str(idx + 1)
        attributes = {
            'symbolicNum': tupletDef.find("f:symbolicNum", namespaces=ns).text,
            'symbolicDur': tupletDef.find("f:symbolicDur", namespaces=ns).text,
            'refNum': tupletDef.find("f:refNum", namespaces=ns).text,
            'refDur': tupletDef.find("f:refDur", namespaces=ns).text,
            'count': 0,
            'number': number,
        }
        SubElement(notations, 'tuplet', number=number, type='start')
        # todo handle nested tuplets
        return attributes


def handleSmartShapeDetail(root, entry, notations):
    entnum = entry.get("entnum")
    smartShapeEntryMarks = root.xpath(f"/f:finale/f:details/f:smartShapeEntryMark[@entnum = '{entnum}']", namespaces=ns)
    for smartShapeEntryMark in smartShapeEntryMarks:
        shapeNum = smartShapeEntryMark.find('f:shapeNum', namespaces=ns).text
        smartShape = root.xpath(f"/f:finale/f:others/f:smartShape[@cmper = '{shapeNum}']", namespaces=ns)[0]
        shapeType = smartShape.find("f:shapeType", namespaces=ns).text if smartShape.find("f:shapeType",
                                                                                          namespaces=ns) is not None else None
        startEntry = smartShape.find("f:startTermSeg/f:endPt/f:entryNum", namespaces=ns).text
        endEntry = smartShape.find("f:startTermSeg/f:endPt/f:entryNum", namespaces=ns).text

        if shapeType == 'slurAuto' or shapeType == 'slurUp':
            slur_type = 'start' if startEntry == entnum else 'stop'
            SubElement(notations, 'slur', number='1', type=slur_type)


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


def add_rest_to_empty_measure(root, measure, meas_spec_cmper):
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
        SubElement(note, "voice").text = '1'
        SubElement(note, "type").text = type_name
        for _ in range(nb_dots):
            SubElement(note, "dot")


def process_entry(root, measure, entry, voice, key, key_adjust, tuplet_attributes):
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

            if idx == 0:
                notations = SubElement(note, "notations")
                if smartShapeDetail:
                    handleSmartShapeDetail(root, entry, notations)
                if tupletStart:
                    tuplet_attributes = handleTupletStart(root, entry, notations)
                if tuplet_attributes:
                    do_tuplet_count(tuplet_attributes, dura)
                    time_modification = SubElement(note, "time-modification")
                    SubElement(time_modification, "actual-notes").text = tuplet_attributes['symbolicNum']
                    SubElement(time_modification, "normal-notes").text = tuplet_attributes['refNum']
                    if tuplet_attributes['count'] == int(tuplet_attributes['symbolicNum']):
                        SubElement(notations, 'tuplet', number=tuplet_attributes['number'], type='stop')
                        tuplet_attributes = None

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

    return tuplet_attributes
