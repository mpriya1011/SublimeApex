import sublime
import os
import sys
import json
import csv
import urllib
import pprint
import xml.dom.minidom

try:
    from . import message
    from . import xmltodict
    from .. import context
except:
    import message
    import xmltodict
    import context

from xml.sax.saxutils import unescape

def sublime_error_message(result):
    message = ''
    if "errorCode" in result:
        message += "Error Code: " + result["errorCode"] + "\n"

    try:
        parsed_result = urllib.parse.unquote(
            unescape(result["message"], {
                "&apos;": "'", 
                "&quot;": '"'
            }))
    except:
        parsed_result = urllib.unquote(
            unescape(result["message"], {
                "&apos;": "'", 
                "&quot;": '"'
            }))

    message += "Error Message: " + parsed_result
    sublime.set_timeout(lambda:sublime.error_message(message), 10)
    
def sublime_status_message(message):
    sublime.set_timeout(lambda:sublime.status_message(message), 10)

def none_value(value):
    """
    If value is None, return "", if not, return value

    @value: value
    """

    if value == None:
        return ""
    return value
    
def parse_test_result(result):
    """
    format test result as specified format

    @result: Run Test Request result

    :return: formated string
    """

    separate = "-" * 100
    view_result = ' Test Result\n'
    class_name = ""
    for test_result in result:
        view_result += separate + "\n"
        view_result += "% 30s    " % "MethodName: "
        view_result += "%-30s" % none_value(test_result["MethodName"]) + "\n"
        view_result += "% 30s    " % "TestTimestamp: "
        view_result += "%-30s" % none_value(test_result["TestTimestamp"]) + "\n"
        view_result += "% 30s    " % "ApexClass: "
        class_name = test_result["ApexClass"]["Name"]
        view_result += "%-30s" % class_name + "\n"
        view_result += "% 30s    " % "Pass/Fail: "
        view_result += "%-30s" % none_value(test_result["Outcome"]) + "\n"
        view_result += "% 30s    " % "Error Message: "
        view_result += "%-30s" % none_value(test_result["Message"]) + "\n"
        view_result += "% 30s    " % "Stack Trace: "
        view_result += "%-30s" % none_value(test_result["StackTrace"]) + "\n"

    return class_name + view_result

def parse_validation_rule(toolingapi_settings, sobjects):
    """
    Parse the validation rule in Sobject.object to csv

    @toolingapi_settings: toolingapi.sublime-settings reference
    @sobject: sobject name
    @validation_rule_path: downloaded objects path by Force.com IDE or ANT
    """

    # Open target file
    outputdir = toolingapi_settings["workspace"] + "/describe/validation rules"
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    # Create or Edit csv File
    fp_validationrules = open(outputdir + "/validation rules.csv", "a", newline='')

    # Initiate CSV Writer and Write headers
    columns = toolingapi_settings["validation_rule_columns"]
    dict_write = csv.DictWriter(fp_validationrules, columns)
    dict_write.writer.writerow([v.capitalize() for v in columns])

    # Open workflow source file
    validation_rule_path = toolingapi_settings["workspace"] + "/metadata/unpackaged/objects"
    for sobject in sobjects:
        try:
            fp = open(validation_rule_path + "/" + sobject + ".object", "rb")
        except IOError:
            # If one sobject is not exist, We don't need do anything
            continue

        result = xmltodict.parse(fp.read())
        fp.close()
        
        ######################################
        # Rules Part
        ######################################
        try:
            rules = result["CustomObject"]["validationRules"]
        except KeyError:
            # If one sobject doesn't have vr, We don't need do anything
            pass

        # Write rows
        write_metadata_to_csv(dict_write, columns, rules, sobject)

    # Close fp
    fp_validationrules.close()

def parse_workflow_metadata(toolingapi_settings, sobject):
    """
    Parse Sobject.workflow to csv, including rule, field update and alerts

    @toolingapi_settings: toolingapi.sublime-settings reference
    @sobject: sobject name
    @workflow_metadata_path: downloaded workflow path by Force.com IDE or ANT
    """
    # Open workflow source file
    workflow_metadata_path = toolingapi_settings["workspace"] + "/metadata/unpackaged/workflows"
    try:
        fp = open(workflow_metadata_path + "/" + sobject + ".workflow", "rb")
    except IOError:
        return

    # Outputdir for save workflow rule, field update, email alert
    # and outbound message and task
    outputdir = toolingapi_settings["workspace"] + "/describe/workflows"
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    # Convert xml to dict
    result = xmltodict.parse(fp.read())
    fp.close()

    ######################################
    # Rules Part
    ######################################
    try:
        rules = result["Workflow"]["rules"]
    except KeyError:
        return

    # Initiate CSV Writer and Write headers
    columns = toolingapi_settings["workflow_rule_columns"]
    fp = open(outputdir + "/" + sobject + " workflow rule.csv", "w", newline='')
    dict_write = csv.DictWriter(fp, columns)
    dict_write.writer.writerow([v.capitalize() for v in columns])

    # Write rows
    write_metadata_to_csv(dict_write, columns, rules, sobject)

    # Close fp
    fp.close()

    ######################################
    # Field Update Part
    ######################################
    try:
        fieldUpdates = result["Workflow"]["fieldUpdates"]
    except KeyError:
        return

    # Initiate CSV Writer and Write headers
    columns = toolingapi_settings["workflow_field_update_columns"]
    fp = open(outputdir + "/" + sobject + " workflow field update.csv", "w", newline='')
    dict_write = csv.DictWriter(fp, columns)
    dict_write.writer.writerow([v.capitalize() for v in columns])

    # Write rows
    write_metadata_to_csv(dict_write, columns, fieldUpdates, sobject)

    # Close fp
    fp.close()

    ######################################
    # Email Alert Part
    ######################################
    try:
        alerts = result["Workflow"]["alerts"]
    except KeyError:
        return

    # Initiate CSV Writer and Write headers
    columns = toolingapi_settings["workflow_email_alert_columns"]
    fp = open(outputdir + "/" + sobject + " email alert.csv", "w", newline='')
    dict_write = csv.DictWriter(fp, columns)
    dict_write.writer.writerow([v.capitalize() for v in columns])

    # Write rows
    write_metadata_to_csv(dict_write, columns, alerts, sobject)

    # Close fp
    fp.close()

    ######################################
    # Outbound Message Part
    ######################################
    try:
        outboundMessages = result["Workflow"]["outboundMessages"]
    except KeyError:
        return

    # Initiate CSV Writer and Write headers
    columns = toolingapi_settings["workflow_outbound_message_columns"]
    fp = open(outputdir + "/" + sobject + " outbound message.csv", "w", newline='')
    dict_write = csv.DictWriter(fp, columns)
    dict_write.writer.writerow([v.capitalize() for v in columns])

    # Write rows
    write_metadata_to_csv(dict_write, columns, outboundMessages, sobject)

    # Close fp
    fp.close()

    ######################################
    # Task Part
    ######################################
    try:
        tasks = result["Workflow"]["tasks"]
    except KeyError:
        return

    # Initiate CSV Writer and Write headers
    columns = toolingapi_settings["workflow_task_columns"]
    fp = open(outputdir + "/" + sobject + " task.csv", "w", newline='')
    dict_write = csv.DictWriter(fp, columns)
    dict_write.writer.writerow([v.capitalize() for v in columns])

    # Write rows
    write_metadata_to_csv(dict_write, columns, tasks, sobject)

    # Close fp
    fp.close()

def write_metadata_to_csv(dict_write, columns, metadata, sobject):
    """
    this method is invoked by function in this module

    @fp: output csv file open reference
    @columns: your specified metadata workbook columns in settings file
    @metadata: metadata describe
    """

    # If sobject has only one rule, it will be dict
    # so we need to convert it to list
    if isinstance(metadata, dict):
        metadata_temp = [metadata]
        metadata = metadata_temp

    # We just use sobject as column, 
    # it's value is assigned with sobject parameter
    columns = [col for col in columns if col != "sobject"]

    for rule in metadata:
        row_value = [sobject]
        for key in columns:
            # Because Workflow rule criteria has different type
            # If key is not in rule, just append ""
            if key not in rule.keys():
                row_value.append("")
                continue

            cell_value = rule[key]
            if isinstance(cell_value, list):
                value = ''
                if len(cell_value) > 0:
                    if isinstance(cell_value[0], dict):
                        values = []
                        for cell_dict in cell_value:
                            for cell_dict_key in cell_dict.keys():
                                values.append(cell_dict[cell_dict_key])
                            value += " ".join(values) + "\n"
                    else:
                        value = " ".join(cell_value) + "\n"

                    cell_value = value[ : -1]
                else:
                    cell_value = ""

            elif isinstance(cell_value, dict):
                value = ''
                for cell_key in cell_value.keys():
                    if cell_value[cell_key] == None:
                        value += cell_key + ": ' '" + "\n"
                    else:
                        value += cell_key + ": " + cell_value[cell_key] + "\n"

                cell_value = value[ : -1]

            elif cell_value == None:
                cell_value = ""

            else:
                cell_value = "%s" % cell_value
                cell_value = cell_value.replace("\r\n", ", ")

            # Unescape special code to normal
            cell_value = urllib.parse.unquote(unescape(cell_value, {"&apos;": "'", "&quot;": '"'}))

            # Append cell_value to list in order to write list to csv
            row_value.append(cell_value)

        # Write row
        dict_write.writer.writerow(row_value)

def list2csv(fp, records):
    """
    convert simple dict in list to csv

    @records: [{"1": 1}, {"2": 2}]
    """
    # If records size is 0, just return
    if len(records) == 0: return "No Custom Fields"
    
    fields_key = records[0].keys()
    sorted(fields_key)

    # Initate CSV Write
    dict_write = csv.DictWriter(fp, fields_key, quoting=csv.QUOTE_ALL)

    # Headers Part, capitalize all headers
    headers = [column.capitalize() for column in fields_key]
    dict_write.writer.writerow(headers)

    # Body Part
    for record in records:
        # If v is None, assign "" to it, and then convert it to str, and then encode it with utf-8
        dict_write.writerow(dict((k, ('%s' % (v and v or ""))) for k, v in record.items()))

    # Release fp
    fp.close()

def parse_describe_layout_result(fp, result):
    """
    parse layout describe result, 
    three part: 
        1. Edit Layouts, 
        2. View Layouts
        3. Available Picklist Value

    up to now, only the Available Picklist Value part is available

    @result: page layout describe result of specified record type
    """
    #########################################
    # Available Picklist Values for recordtype
    #########################################
    try:
        picklistsForRecordType = result["recordTypeMappings"]["picklistsForRecordType"]
    except KeyError:
        fp.write("No available picklist field.")
        fp.close()
        return
    
    headers = ["Picklist Field", "Available Values"]
    dict_write = csv.DictWriter(fp, headers, quoting=csv.QUOTE_ALL)

    # Write headers
    dict_write.writer.writerow(headers)

    # Write body
    for picklist in picklistsForRecordType:
        field_name = picklist["picklistName"]
        picklistValues = picklist["picklistValues"]

        values = []
        if isinstance(picklistValues, dict):
            values.append(picklistValues["value"])
        elif isinstance(picklistValues, list):
            values = [p["value"] for p in picklistValues]
        value = "\n".join(values)

        # Write row
        dict_write.writer.writerow([field_name, value])

    # Close fp
    fp.close()

def parse_execute_anonymous_xml(result):
    """
    Get the compile result in the xml result

    @result: execute anonymous result, it's a xml

    @return: formated string
    """

    compiled = result["compiled"]
    debugLog = result["debugLog"]

    view_result = ''
    if compiled == "true":
        view_result = debugLog
    elif compiled == "false":
        line = result["line"]
        column = result["column"]
        compileProblem = result["compileProblem"]
        view_result = compileProblem + " at line " + line +\
            " column " + column + "\n" + "-" * 100 + "\n" + debugLog
        print(view_result)

    return urllib.parse.unquote(unescape(view_result, {"&apos;": "'", "&quot;": '"'}))

def generate_workbook(result, workspace, workbook_field_describe_columns):
    """
    generate workbook for sobject according to user customized columns
    you can change the workbook_field_describe_columns in default settings

    @result: sobject describe result
    @workspace: your specified workspace in toolingapi.sublime-settings
    @workflow_field_update_columns: your specified workbook columns in toolingapi.sublime-settings
    """
    # Get sobject name
    sobject = result.get("name")

    # Get fields
    fields = result.get("fields")
    fields_key = workbook_field_describe_columns

    # If workbook path is not exist, just make it
    outputdir = workspace + "/describe/sobject workbooks"
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    # Create new csv file for this workbook
    # fp = open(outputdir + "/" + sobject + ".csv", "wb", newline='')
    fp = open(outputdir + "/" + sobject + ".csv", "w", newline='')
    
    #------------------------------------------------------------
    # Headers, all headers are capitalized
    #------------------------------------------------------------
    headers = [column.capitalize() for column in fields_key]
    dict_write = csv.DictWriter(fp, headers, quoting=csv.QUOTE_ALL)
    dict_write.writer.writerow(headers)

    #------------------------------------------------------------
    # Fields Part (All rows are sorted by field label)
    #------------------------------------------------------------
    fields = sorted(fields, key=lambda k : k['label'])
    for field in fields:
        row = []
        for key in fields_key:
            # Get field value by field API(key)
            row_value = field.get(key)
            
            if isinstance(row_value, list):
                if key == "picklistValues":
                    value = ''
                    if len(row_value) > 0:
                        for item in row_value:
                            value += item.get("value") + "\n"
                        row_value = value
                    else:
                        row_value = ""
                elif key == "referenceTo":
                    if len(row_value) > 0:
                        row_value = row_value[0]
                    else:
                        row_value = ""
            elif row_value == None:
                row_value = ""
            else:
                row_value = "%s" % row_value
                row_value.replace("\r\n", ", ")

            row.append(row_value)

        # Write row to csv
        dict_write.writer.writerow(row)

    # Close fp
    fp.close()

    # Display Success Message
    sublime.set_timeout(lambda:sublime.status_message(sobject + " workbook is generated"), 10)

    # Return outputdir
    return outputdir

seprate = 100 * "-" + "\n"
def parse_execute_query_result(result):
    """
    Parse the soql query result to formated string

    @result: soql query result, it's a dict

    @return: formated string
    """

    def parse_records(value, view_result):
        #------------------------------------------------------------
        # Part of TotalSize, Title and seprate line
        #------------------------------------------------------------
        # Get the field list of record and remove attributes
        records = value["records"]
        record_keys = records[0].keys()
        record_keys = [ele for ele in record_keys if ele != "attributes"]

        # Append columns part into view_result
        columns = ""
        for key in record_keys:
            columns += "%-30s" % key

        view_result += records[0]["attributes"]["type"] + " totalSize: \t" +\
            str(value.get("totalSize")) + "\n"
        view_result += seprate
        view_result += columns + "\n" + len(columns) * "-" + "\n"

        #------------------------------------------------------------
        # Part of Field Value
        #------------------------------------------------------------
        for record in value.get("records"):
            row = ""
            for key in record_keys:
                # Get field value by field API
                row_value = record.get(key)
                if row_value == None:
                    row_value = ""

                row_value = "%-30s" % row_value
                row += row_value
            view_result += row + "\n"
            
        return view_result

    # If no query result, just...
    if "totalSize" in result and result.get("totalSize") == 0:
        return "No query result."

    parent_view_result = ""
    parent_view_result = parse_records(result, parent_view_result)

    child_view_result = ""
    for parent_record in result["records"]:
        for key in parent_record.keys():
            if key == "attributes":
                continue

            value = parent_record[key]
            if isinstance(value, dict) and value != None:
                child_view_result = parse_records(value, child_view_result)
                child_view_result += "\n"

    return parent_view_result + child_view_result

record_keys = ["label", "name", "type", "length"]
record_key_width = {
    "label": 40, 
    "name": 40, 
    "type": 15, 
    "length": 2
}
recordtype_key_width = {
    "available": 10,
    "recordTypeId": 20,
    "name": 35,
    "defaultRecordTypeMapping": 15
}
childrelationship_key_width = {
    "field": 35,
    "relationshipName": 35,
    "childSObject": 30,
    "cascadeDelete": 12
}

def parse_sobject_field_result(result):
    """
    According to sobject describe result, display recordtype information, child sobjects 
    information and the field information.

    @result: sobject describe information, it's a dict

    @return: formated string including the three parts
    """

    # Get sobject name
    sobject = result.get("name")

    # View Name or Header
    view_result = sobject + " Describe:\n"

    #------------------------------------------------
    # Record Type Part
    #------------------------------------------------
    recordtypes = result.get("recordTypeInfos")
    view_result += seprate
    view_result += "Record Type Info: \t" + str(len(recordtypes)) + "\n"
    view_result += seprate

    # Get Record Type Info Columns
    recordtype_keys = []
    if len(recordtypes) > 0:
        recordtype_keys = recordtypes[0].keys()

    columns = ""
    for key in recordtype_keys:
        key_width = recordtype_key_width[key]
        if key == "defaultRecordTypeMapping": key = "default"
        columns += "%-*s" % (key_width, key.capitalize())

    view_result += columns + "\n"
    view_result += len(columns) * "-" + "\n"

    for recordtype in recordtypes:
        row = ""
        for key in recordtype_keys:
            # Get field value by field API
            # and convert it to str
            row_value = recordtype.get(key)
            if row_value == None:
                row_value = ""

            key_width = recordtype_key_width[key]
            row_value = "%-*s" % (key_width, row_value)
            row += row_value
            
        view_result += row + "\n"

    view_result += "\n"

    #------------------------------------------------
    # Child Relationship
    #------------------------------------------------
    childRelationships = result.get("childRelationships")
    view_result += seprate
    view_result += "ChildRelationships Info: \t" + str(len(childRelationships)) + "\n"
    view_result += seprate

    # Get Record Type Info Columns
    childRelationships_keys = childrelationship_key_width.keys()
    print (childRelationships_keys)
    columns = ""
    for key in childRelationships_keys:
        columns += "%-*s" % (30, key.capitalize())

    view_result += columns + "\n"
    view_result += len(columns) * "-" + "\n"

    for childRelationship in childRelationships:
        row = ""
        for key in childRelationships_keys:
            # Get field value by field API
            # and convert it to str
            row_value = childRelationship.get(key)
            if row_value == None:
                row_value = ""

            row_value = "%-*s" % (30, row_value)
            row += row_value
            
        view_result += row + "\n"

    view_result += "\n"

    #------------------------------------------------
    # Fields Part
    #------------------------------------------------
    # Output totalSize Part
    fields = result.get("fields")
    view_result += seprate
    view_result += "Total Fields: \t" + str(len(fields)) + "\n"
    view_result += seprate

    # Ouput Title and seprate line
    columns = ""
    for key in record_keys:
        key_width = record_key_width[key]
        columns += "%-*s" % (key_width, key.capitalize())

    view_result += columns + "\n"
    view_result += len(columns) * "-" + "\n"

    # Sort fields list by lable of every field
    fields = sorted(fields, key=lambda k : k['label'])

    # Output field values
    for record in fields:
        row = ""
        for key in record_keys:
            row_value = record.get(key)
            if row_value == None:
                row_value = ""

            key_width = record_key_width[key]
            row_value = "%-*s" % (key_width, row_value)
            row += row_value

        view_result += row + "\n"

    return view_result

def getUniqueElementValueFromXmlString(xmlString, elementName):
    """
    Extracts an element value from an XML string.
    
    For example, invoking 
    getUniqueElementValueFromXmlString('<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>', 'foo')
    should return the value 'bar'.
    """
    xmlStringAsDom = xml.dom.minidom.parseString(xmlString)
    elementsByName = xmlStringAsDom.getElementsByTagName(elementName)
    elementValue = None
    if len(elementsByName) > 0:
        elementValue = elementsByName[0].toxml().replace('<' + elementName + '>','').replace('</' + elementName + '>','')
    return elementValue
    
# Get component_name (Class Name, Trigger Name, etc.) by file_name
def get_component_name(file_name):
    """
    Get the Component name by file_name

    @file_name: local component full file name, for example:
    D:\ForcedotcomWorkspace\pro-exercise-20130625\ApexClass\AccountChartController.cls
    component name is AccountChartController

    @return: component name
    """

    # Get the position of .
    dot_position = file_name.rfind(".")

    # if file has no extension, so 
    dot_position = dot_position == -1 and len(file_name) or dot_position

    # Get component_name
    component_name = file_name[file_name.rfind("\\") + 1 : dot_position]

    return component_name

# Get component type by file_name
def get_component_type(file_name):
    """
    Get the Component type by file_name

    @file_name: local component full file name, for example:
    D:\ForcedotcomWorkspace\pro-exercise-20130625\ApexClass\AccountChartController.cls
    component type is ApexClass

    @return: component type
    """

    location_of_last_backslash = file_name.rfind("\\")
    component_type = file_name[file_name[0 :\
        location_of_last_backslash - 1].rfind("\\") + 1 : location_of_last_backslash]

    return component_type

def get_component_url_and_id(file_name):
    """
    get the component name by file_name, and then get the component_url and component_id
    by component name and local settings

    @file_name: local component full file name, for example:
    D:\ForcedotcomWorkspace\pro-exercise-20130625\ApexClass\AccountChartController.cls

    @return: tuple(component_url, component_id)
    """

    # Get component type and component name
    component_type = get_component_type(file_name)
    component_name =  get_component_name(file_name)

    # Load metadata settings
    component_settings = sublime.load_settings(context.COMPONENT_METADATA_SETTINGS)

    # Get Component attribute by component_name
    component_attribute = component_settings.get(component_type + component_name)
    print(component_name + ": ", component_attribute)

    # If this component_name is not exist in component_settings
    if component_attribute == None:
        sublime.error_message(message.DOWNLOAD_ALL_FIRST)
        return None, None

    # Get metadata Id and metadata get_component_url_and_idRL
    component_url = component_attribute.get("component_url")
    component_id = component_attribute.get("component_id")

    # Return tuple
    return component_url, component_id