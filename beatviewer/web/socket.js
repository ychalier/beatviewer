class ArgumentParser {
    constructor() {
        this.arguments = [];
    }
    
    add_argument(name, default_, type, choices=null) {
        this.arguments.push({
            name: name,
            default: default_,
            type: type,
            choices: choices
        });
    }

    parse_args() {
        let params = new URLSearchParams(window.location.search);
        let args = {};
        this.arguments.forEach(arg => {
            let value = arg.default;
            if (params.has(arg.name)) {
                let raw_value = params.get(arg.name);
                if (arg.type == "string") {
                    value = raw_value;
                } else if (arg.type == "int") {
                    value = parseInt(raw_value);
                } else if (arg.type == "float") {
                    value = parseFloat(raw_value);
                }
            }
            if (arg.choices && !arg.choices.includes(value)) {
                value = arg.default;
            }
            args[arg.name] = value;
        });
        console.log("Parsed args:", args);
        return args;
    }

}

function parse_args(defaults) {
    let params = new URLSearchParams(window.location.search);
    let args = {};
    for (let key in defaults) {
        let reference = defaults[key];
        if (params.has(key)) {
            let value = params.get(key);
            if (typeof reference === "string") {
                args[key] = value;
            } else {
                args[key] = parseFloat(value);
            }
        } else {
            args[key] = reference;
        }
    }
    return args;
}

function connect_socket_server(server_uri, beat_callback, onset_callback, bpm_callback) {              
    const socket = new WebSocket(server_uri);
    socket.binaryType = "arraybuffer";

    socket.addEventListener("open", () => {
        console.log("Connected to socket server!");
    });

    socket.addEventListener("error", () => {
        console.warn("Could not connect to socket server, retrying in 1s");
        setTimeout(() => {
            connect_socket_server(server_uri, beat_callback, onset_callback, bpm_callback);
        }, 1000);
    });

    socket.addEventListener("message", (event) => {
        const view = new DataView(event.data);
        const value = view.getInt16(0, false);
        if (value == 0) {
            if (beat_callback) beat_callback();
        } else if (value == 1) {
            if (onset_callback) onset_callback();
        } else {
            if (bpm_callback) bpm_callback(value);
        }
        socket.send("k");
    });

    socket.addEventListener("close", () => {
        console.warn("Socket was closed");
    });

}
