# Instagram Follow-Back Automation

A Python script to manage Instagram follow relationships. It processes a list of profiles from a CSV, checks your relationship status, and automates "Follow Back" actions where appropriate.

## Features

- **Automated Relationship Management**:
  - Detects if you are following a user.
  - Handles "Unfollow" processing to check for "Follow Back" opportunities.
  - Automatically clicks "Follow Back" if the user follows you.
  - Updates status to "Not Following" if the user does not follow you back.
- **Robust Automation**:
  - Uses **Playwright** for reliable browser interaction.
  - Handles Instagram's "Unfollow" confirmation popups.
  - Waits logic to ensure state changes are captured correctly.
- **Session Persistence**:
  - Saves browser cookies/session to `instagram_user_data` to avoid repeated logins.
  - Supports 2FA (pauses for manual code entry if required).
- **Progress Tracking**:
  - Updates a local CSV file (`_updated.csv`) row-by-row to ensure data safety.

## Requirements

- Python 3.8+
- [Playwright](https://playwright.dev/python/)

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/anup-raghavan/instagram_unfollower.git
    cd instagram_unfollower
    ```

2.  **Install dependencies**:
    ```bash
    pip install pandas playwright
    playwright install chromium
    ```

## Usage

1.  **Prepare your Input CSV**:
    Create a CSV file with at least the following columns:
    - `Username`
    - `Instagram Link` (Full URL, e.g., `https://www.instagram.com/username/`)
    - `Date Followed` (Optional but recommended for your reference)

2.  **Run the Script**:
    ```bash
    python main.py
    ```

3.  **Follow Prompts**:
    - Enter the path to your CSV file when prompted.
    - **First Run**: Log in to Instagram in the opened browser window. Complete 2FA if requested.
    - **Subsequent Runs**: The script will automatically use the saved session.

## Output

The script generates an output file (e.g., `input_filename_updated.csv`) with a new `Status` column:
- `Following`: You successfully followed back the user.
- `Not Following`: You unfollowed the user (or they don't follow you).
- `Not Found`: The profile link is broken or page is unavailable.
- `Error`: Something went wrong processing this row.

## Disclaimer

This tool is for educational purposes. Use responsible automation settings to avoid flagging your Instagram account.
