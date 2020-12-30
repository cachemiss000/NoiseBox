import {MessageNames, ValueError} from "../../client/messageNames"

test("gets right name", () => {
    const name = MessageNames.messageTypeToName("ListPlaylistsCommand")
    expect(name).toBe("LIST_PLAYLISTS")
})

test("returns value for all classes", () => {
    for (const name of MessageNames.validV1MessageNames()) {
        expect(MessageNames.messageTypeToName(name)).toBeTruthy()
    }
})

test("has disjoint command and event names", () => {
    const eventNames = MessageNames.validV1EventNames()
    for (let name of MessageNames.validV1CommandNames()) {
        expect(eventNames.includes(name)).toBeFalsy()
    }
})

test("has Event names all end in 'event'", () => {
    const ends_in_event = /.*Event$/
    for (let name of MessageNames.validV1EventNames()) {
        expect(name).toMatch(ends_in_event)
    }
})

test("has Command names all end in 'command'", () => {
    const ends_in_command = /.*Command$/
    for (let name of MessageNames.validV1CommandNames()) {
        expect(name).toMatch(ends_in_command)
    }
})

test("All messages covered by events and commands", () => {
    const messageNames = MessageNames.validV1MessageNames()
    for (let name of MessageNames.validV1CommandNames()) {
        expect(messageNames.includes(name)).toBeTruthy()
    }
    for (let name of MessageNames.validV1EventNames()) {
        expect(messageNames.includes(name)).toBeTruthy()
    }
})

test("throws for invalid name", () => {
    expect(() => MessageNames.messageTypeToName("florbus")).toThrow(ValueError)
})

test("events from EVENT_NAME behave sanely", () => {
    // Hard coding one example so that we can be sure it's returning something that looks vaguely right.
    expect(MessageNames.nameToMessageType("PLAY_STATE")).toBe("PlayStateEvent")
})

test("commands from COMMAND_NAME behave sanely", () => {
    // Hard coding one example so that we can be sure it's returning something that looks vaguely right.
    expect(MessageNames.nameToMessageType("TOGGLE_PLAY")).toBe("TogglePlayCommand")
})

test("EVENT_NAME from event type behaves sanely", () => {
    // Hard coding one example so that we can be sure it's returning something that looks vaguely right.
    expect(MessageNames.messageTypeToName("PlayStateEvent")).toBe("PLAY_STATE")
})

test("COMMAND_NAME from command type behaves sanely", () => {
    // Hard coding one example so that we can be sure it's returning something that looks vaguely right.
    expect(MessageNames.messageTypeToName("TogglePlayCommand")).toBe("TOGGLE_PLAY")
})

test("Empty nameToMessageType arg throws ValueError", () => {
    expect(() => MessageNames.messageTypeToName(null)).toThrow(ValueError)
})

test("Empty messageTypeToName arg throws ValueError", () => {
    expect(() => MessageNames.nameToMessageType(null)).toThrow(ValueError)
})

test("Invalid nameToMessageType arg throws type error", () => {
    expect(() => MessageNames.nameToMessageType("florbus")).toThrow(ValueError)
})
