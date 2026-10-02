from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from brochure_catalog import list_brochures


def brochure_keyboard(selected_keys) -> InlineKeyboardMarkup:
    rows = []
    for brochure in list_brochures():
        check = "✅" if brochure.key in selected_keys else "⬜"
        rows.append(
            [InlineKeyboardButton(f"{check} {brochure.label}", callback_data=f"toggle:{brochure.key}")]
        )
    rows.append([InlineKeyboardButton("Continue ➡️", callback_data="continue")])
    return InlineKeyboardMarkup(rows)


def confirmation_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("Edit Name", callback_data="edit:name"),
            InlineKeyboardButton("Edit Company", callback_data="edit:company"),
        ],
        [
            InlineKeyboardButton("Edit Phone", callback_data="edit:phone"),
            InlineKeyboardButton("Edit Email", callback_data="edit:email"),
        ],
        [
            InlineKeyboardButton("✅ Send", callback_data="confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
        ],
    ]
    return InlineKeyboardMarkup(rows)
