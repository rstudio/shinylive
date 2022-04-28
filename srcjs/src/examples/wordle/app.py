# pyright: reportUnusedFunction=false

import os.path
import random
from typing import TypedDict, cast

import shiny
from htmltools import TagList, div, h3, head_content, tags
from shiny import Inputs, Outputs, Session, event, reactive, render_ui, ui
from typing_extensions import Literal

import words

LetterMatch = Literal["correct", "in-word", "not-in-word"]


class GuessInfo(TypedDict):
    word: str
    letters: list[str]
    match_types: list[LetterMatch]
    win: bool


# Read in a file and return contents as a string.
def read_file(filename: str) -> str:
    with open(filename) as f:
        return " ".join(f.readlines())


app_ui = ui.page_fluid(
    head_content(
        tags.meta(name="viewport", content="width=device-width, initial-scale=1.0"),
        tags.style(read_file(os.path.join(os.path.dirname(__file__), "style.css"))),
    ),
    div(
        h3("Shiny Wordle"),
        ui.output_ui("previous_guesses"),
        ui.output_ui("current_guess"),
        ui.output_ui("endgame"),
        ui.output_ui("new_game_ui"),
        class_="guesses",
    ),
    ui.output_ui("keyboard"),
    # div(input_checkbox("hard", "Hard mode"), style="display: inline-block;"),
    tags.script(
        """
    const letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                     'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'];
    const all_key_ids = [ ...letters, 'Enter', 'Back'];
    document.addEventListener('keydown', function(e) {
      let key = e.code.replace(/^Key/, '');
      if (letters.includes(key)) {
        document.getElementById(key).click();
      } else if (key == 'Enter') {
        document.getElementById('Enter').click();
      } else if (key == 'Backspace') {
        document.getElementById('Back').click();
      }
    });

    // For better responsiveness on touch devices, trigger a click on the button
    // when a touchstart event occurs; don't wait for the touchend event. So
    // that a click event doesn't happen when the touchend event happens (and
    // cause the letter to be typed a second time), we set the 'pointer-events'
    // CSS property to 'none' on the button. Then when there's _any_ touchend
    // event, unset the 'pointer-events' CSS property on all of the buttons, so
    // that the button can be touched again.
    let in_button_touch = false;
    document.addEventListener('touchstart', function(e) {
        if (all_key_ids.includes(e.target.id)) {
            e.target.click();
            e.target.style.pointerEvents = 'none';
            e.preventDefault();   // Disable text selection
            in_button_touch = true;
        }
    });
    document.addEventListener('touchend', function(e) {
        all_key_ids.map((id) => {
            document.getElementById(id).style.pointerEvents = null;
        });
        if (in_button_touch) {
            if (all_key_ids.includes(e.target.id)) {
                // Disable text selection and triggering of click event.
                e.preventDefault();
            }
            in_button_touch = false;
        }
    });
    """
    ),
    title="Shiny Wordle",
)


class ShinyInputs(Inputs):
    Enter: reactive.Value[int]
    Back: reactive.Value[int]
    new_game: reactive.Value[int]
    hard: reactive.Value[bool]


def server(input: Inputs, output: Outputs, session: Session):
    input = cast(ShinyInputs, input)

    target_word = reactive.Value(random.choice(tuple(words.targets)))
    all_guesses = reactive.Value(list[GuessInfo]())
    finished = reactive.Value(False)
    current_guess_letters = reactive.Value(list[str]())

    def reset_game():
        target_word.set(random.choice(tuple(words.targets)))
        all_guesses.set(list[GuessInfo]())
        finished.set(False)

    # ==========================================================================
    # UI displaying guesses
    # ==========================================================================
    @output()
    @render_ui()
    def previous_guesses() -> TagList:
        res = TagList()
        for guess in all_guesses():
            letters = guess["letters"]

            row = div(class_="word")
            for i in range(len(letters)):
                match = guess["match_types"][i]
                row.children.append(div(letters[i].upper(), class_="letter " + match))
            res.append(row)

        # Add JS code to scroll to bottom
        scroll_js = """
            document.querySelector('.guesses')
              .scrollTo(0, document.querySelector('.guesses').scrollHeight);
        """
        res.append(tags.script(scroll_js))

        return res

    @output()
    @render_ui()
    def current_guess():
        if finished():
            return

        letters = current_guess_letters().copy()

        # Fill in blanks for letters up to length of target word. If letters is:
        #   "a" "r"
        # then result is:
        #   "a" "r" "" "" ""
        with reactive.isolate():
            target_length = len(target_word())
        for _i in range(target_length - len(letters)):
            letters.append("")

        res = div(class_="word")
        for i in range(target_length):
            res.children.append(div(letters[i].upper(), class_="letter guess"))

        return res

    @reactive.Calc()
    def used_letters() -> dict[str, LetterMatch]:
        # This is a dictionary. The structure will be something like:
        # {"p": "not-in-word", "a": "in-word", "e": "correct")
        letter_matches: dict[str, LetterMatch] = {}

        # Populate `letter_matches` by iterating over all letters in all the guesses.
        for guess in all_guesses():
            for i in range(len(guess["letters"])):
                letter = guess["letters"][i]
                match_type = guess["match_types"][i]
                if letter not in letter_matches:
                    # If there isn't an existing entry for that letter, just use it.
                    letter_matches[letter] = match_type
                else:
                    prev_match_type = letter_matches[letter]
                    if match_type == "correct" and prev_match_type in [
                        "not-in-word",
                        "in-word",
                    ]:
                        # If an entry is already present, it can be "upgraded":
                        # "not-in-word" < "in-word" < "correct"
                        letter_matches[letter] = match_type
                    elif match_type == "in-word" and prev_match_type in ["not-in-word"]:
                        letter_matches[letter] = match_type

        return letter_matches

    # ==========================================================================
    # Keyboard input
    # ==========================================================================
    keys = [
        ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
        ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
        ["Enter", "Z", "X", "C", "V", "B", "N", "M", "Back"],
    ]

    @output()
    @render_ui()
    def keyboard():
        prev_match_type = used_letters()
        keyboard_div = div(class_="keyboard")
        for row_keys in keys:
            row_div = div(class_="keyboard-row")
            for key in row_keys:
                class_ = "key"
                if key.lower() in prev_match_type:
                    class_ += " " + prev_match_type[key.lower()]
                if key in ["Enter", "Back"]:
                    class_ += " wide-key"

                key_button = ui.input_action_button(key, key)
                key_button.attrs.update(class_=key_button.attrs["class"] + " " + class_)
                row_div.children.append(key_button)

            keyboard_div.children.append(row_div)

        return keyboard_div

    @reactive.Effect()
    @event(input.Back)  # Take a dependency on the Back button
    def _():
        if finished():
            return
        current_letters = current_guess_letters().copy()
        if len(current_letters) > 0:
            current_letters.pop()
            current_guess_letters.set(current_letters)

    @reactive.Effect()
    @event(input.Enter)  # Take a dependency on the Enter button
    def _():
        with reactive.isolate():
            guess = "".join(current_guess_letters())

            if guess not in words.all:
                return

            # if input["hard"]:
            #     # Letters in the target word that the player has previously
            #     # guessed correctly.
            #     matched_letters = used_letters().intersection(set(target_word()))
            #     if not set(guess).issuperset(matched_letters):
            #         return

            all_guesses_new: list[GuessInfo] = all_guesses()
            # This copy is needed because the list is returned by reference, and
            # is a mutable object. If we didn't copy it and simply assigned it
            # back to all_guesses, then it wouldn't invalidate anything that
            # depends on all_guesses.
            all_guesses_new = all_guesses_new.copy()

            check_result = check_word(guess, target_word())
            all_guesses_new.append(check_result)
            all_guesses.set(all_guesses_new)
            all_guesses.set(all_guesses_new)

            if check_result["win"]:
                finished.set(True)

            current_guess_letters.set([])

    # ==========================================================================
    # Create observers to listen to each possible keypress
    # ==========================================================================
    def make_key_listener(key: str):
        @reactive.Effect()
        @event(input[key])
        def _():
            if finished():
                return
            cur_letters = current_guess_letters().copy()
            if len(cur_letters) >= 5:
                return
            cur_letters.append(key.lower())
            current_guess_letters.set(cur_letters)

    for keyboard_row in keys:
        for key in keyboard_row:
            if key == "Enter" or key == "Back":
                continue

            make_key_listener(key)

    @output()
    @render_ui()
    def endgame():
        if not finished():
            return tags.script(
                """
                document.querySelector('.guesses').classList.remove('finished');
                """
            )

        res = div(class_="endgame-content")
        res.append(
            tags.script(
                """
                document.querySelector('.guesses').classList.add('finished');
                """
            )
        )

        for guess in all_guesses():
            line_text = ""
            for match in guess["match_types"]:
                if match == "correct":
                    line_text += "🟩"
                elif match == "in-word":
                    line_text += "🟨"
                elif match == "not-in-word":
                    line_text += "⬜"
            res.children.append(div(line_text))
        return res

    # ==========================================================================
    # New game button
    # ==========================================================================
    @output()
    @render_ui()
    def new_game_ui():
        if finished():
            return ui.input_action_button("new_game", "New Game")

    @reactive.Effect()
    @event(input.new_game)
    def _():
        reset_game()


app = shiny.App(app_ui, server, debug=False)


def check_word(guess_str: str, target_str: str) -> GuessInfo:
    guess = list(guess_str)
    target = list(target_str)
    remaining: list[str] = []

    if len(guess) != len(target):
        raise Exception("Word lengths don't match.")

    result: list[LetterMatch] = ["not-in-word"] * len(guess)

    # First pass: find matches in correct position. Letters in the target that
    # do not match the guess are added to the remaining list.
    for i in range(len(guess)):
        if guess[i] == target[i]:
            result[i] = "correct"
        else:
            remaining.append(target[i])

    # Second pass: find matches in remaining letters, using them up as we find
    # matches in the guess.
    for i in range(len(guess)):
        if guess[i] != target[i] and guess[i] in remaining:
            result[i] = "in-word"
            remaining.remove(guess[i])

    return {
        "word": guess_str,
        "letters": guess,
        "match_types": result,
        "win": all(x == "correct" for x in result),
    }
