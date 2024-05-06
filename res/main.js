var socket;

function send_message(method, data = {}) {
    json_data = {
        "event_type": method,
        "args": data
    };

    console.log("Sending a message: ", json_data);

    socket.send(JSON.stringify(json_data));
}

function reconnect() {
    console.log(`Connecting to ws://${location.host}/ws`)
    socket = new WebSocket("ws://" + location.host + "/ws");

    socket.addEventListener("close", (event) => {
        console.log("WebSocket has disconnected, trying to reconnect");
        reconnect();
    });

    socket.addEventListener("message", (event) => {
        const message = JSON.parse(event.data);

        console.log("Received a message: ", message);

        switch(message["event_type"]) {
            case "status":
                if (message["args"]["registered"]) {
                  show_screen("waiting_to_start_the_game");
                  set_players_name(message["args"]["name"]);
                } else {
                  show_screen("enter_your_name");
                }
            break;
            case "question":
                question(message["args"]["number_of_variants"]);
            break
            case "guessed":
                show_screen("waiting_for_the_next_question_screen");

                set_players_score(message["args"]["score"]);
                set_players_correctness(message["args"]["correct"]);
            break
        }
    });
}

function set_players_name(name) {
    document.getElementById("your_name").textContent = name;
}

function set_players_score(score) {
    document.getElementById("your_score").textContent = score.toString();
}

function set_players_correctness(correct) {
    const correct_answer_div = document.getElementById("correct_answer");
    const incorrect_answer_div = document.getElementById("incorrect_answer");

    if (correct) {
        correct_answer_div.style.display = "auto";
        incorrect_answer_div.style.display = "none";
    }
    else {
        correct_answer_div.style.display = "none";
        incorrect_answer_div.style.display = "auto";
    }
}

function make_a_guess(variant) {
    send_message("guess", {"variant": variant});
}

function question(number_of_variants) {
    const screen = document.getElementById("guess_screen");
    screen.innerHTML = '';

    for (let i = 0; i < number_of_variants; i++) {
        show_screen("guess_screen");

        const button = document.createElement("div");
        button.classList.add("guess_button");
        button.onclick = () => make_a_guess(i);
        const newContent = document.createTextNode(i.toString());
        button.appendChild(newContent);

        screen.appendChild(button);
    }
}


function hide_all_screens() {
    Array.from(document.getElementsByClassName("screen")).forEach(element => {
        element.style.display = "none";
    });
}

function show_screen(element_id) {
    hide_all_screens();
    document.getElementById(element_id).style.display = "flex";
}

function register() {
    const name = document.getElementById("input_name").value;

    if (name == "") {
        return;
    }

    send_message("register", {name: name});
}

function unregister() {
    send_message("unregister");
}