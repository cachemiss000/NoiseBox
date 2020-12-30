import * as fs from "fs";
import {JSONSchema6, JSONSchema6Definition} from "json-schema";
import {memoize} from "lodash";

const FILE_PATH: string = "file://../../schema/commandserver/server_types/v1_command_schema.json";


export class ValueError extends Error {
}

export class MessageNames {
    private static getV1Schema = memoize((): JSONSchema6 => {
        const file_contents = fs.readFileSync(`${FILE_PATH}`, null)
        return JSON.parse(file_contents.toString("utf-8"))
    })

    private static COMMAND_NAME_REGEX = RegExp("^[a-zA-Z_]*Command$")
    private static EVENT_NAME_REGEX = RegExp("^[a-zA-Z_]*Event$")
    private static MESSAGE_NAME_REGEX = RegExp(`((${MessageNames.COMMAND_NAME_REGEX.source})|(${MessageNames.EVENT_NAME_REGEX.source}))`)
    /**
     * Returns all V1 message names (events & commands)
     */
    public static validV1MessageNames = memoize((): string[] => {
        const definitions = MessageNames.getV1Schema().definitions
        const names = []
        for (let key in definitions) {
            if (MessageNames.MESSAGE_NAME_REGEX.test(key)) {
                names.push(key)
            }
        }
        return names
    })
    /**
     * Returns all V1 command names.
     */
    public static validV1CommandNames = memoize((): string[] => {
        return MessageNames.validV1MessageNames().filter((value) => MessageNames.COMMAND_NAME_REGEX.test(value))
    })
    /**
     * Returns all V1 event names.
     */
    public static validV1EventNames = memoize((): string[] => {
        return MessageNames.validV1MessageNames().filter((value) => MessageNames.EVENT_NAME_REGEX.test(value))
    })
    private static getMessageNameToMessageDict = memoize((): Record<string, string> => {
        const message_names: string[] = MessageNames.validV1MessageNames()
        const message_name_map: Record<string, string> = {}

        for (let name of message_names) {
            message_name_map[MessageNames.messageTypeToName(name)] = name
        }
        return message_name_map
    })

    /**
     * Returns the expected event_name or command_name field for a given message_type.
     *
     * Ex:
     *   'TogglePlayCommand' -> TOGGLE_PLAY
     */
    public static messageTypeToName(message_type: string): string {
        const defn = this.getDefinitionFor(message_type)
        if (this.COMMAND_NAME_REGEX.test(message_type)) {
            return this.getCommandNameFromCommand(defn)
        }
        return this.getEventNameFromEvent(defn)
    }

    public static nameToMessageType(command_or_event_name: string): string {
        const message_names_to_types = this.getMessageNameToMessageDict()

        const ret_val = message_names_to_types[command_or_event_name]
        if (!ret_val) {
            throw new ValueError(`Expected ${command_or_event_name} to be in valid 
            message names ${message_names_to_types.keys}`)
        }
        return ret_val
    }

    private static unwrap(defn: JSONSchema6Definition): JSONSchema6 {
        if (typeof (defn) === "boolean") {
            return null
        }
        return defn as JSONSchema6
    }

    private static getDefinitionFor(class_name: string): JSONSchema6Definition {
        if (!MessageNames.MESSAGE_NAME_REGEX.test(class_name)) {
            throw new ValueError(`Expected ${class_name} to end in "Event" or "Command", and be a valid type name`)
        }

        if (!MessageNames.validV1MessageNames().includes(class_name)) {
            throw new ValueError(`Expected ${class_name} to be in ${MessageNames.validV1MessageNames()}`)
        }

        const schema = this.getV1Schema()
        const class_defn = schema.definitions[class_name]

        if (!class_defn) {
            throw new ValueError(`Expected ${class_name} to be in schema definition list `)
        }
        return class_defn
    }

    private static getCommandNameFromCommand(command_defn: JSONSchema6Definition) {
        if (!command_defn) {
            return
        }
        const properties = this.unwrap(command_defn).properties["command_name"]
        return this.unwrap(properties)?.pattern
    }

    private static getEventNameFromEvent(event_defn: JSONSchema6Definition) {
        if (!event_defn) {
            return
        }
        const properties = this.unwrap(event_defn).properties["event_name"]
        return this.unwrap(properties)?.pattern
    }
}
