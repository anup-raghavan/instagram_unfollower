import pandas as pd
from playwright.sync_api import sync_playwright
import time
import os
import getpass
import re

# Constants
Status_UnFollowed = "Unfollowed"
Status_Following = "Following"
Status_NotFound = "Not Found"
Status_Error = "Error"
Status_Skipped = "Skipped" # If row already processed or invalid

def login_to_instagram(page, username, password):
    """
    Logs into Instagram if not already logged in.
    """
    print("Navigating to Instagram login...")
    page.goto("https://www.instagram.com/accounts/login/")
    time.sleep(3) # Wait for initial load

    # Check if already logged in (look for some element, e.g., profile icon or home)
    # This is a basic check; can be improved
    if page.is_visible("svg[aria-label='Home']"):
        print("Already logged in.")
        return True

    try:
        print("Entering credentials...")
        page.fill("input[name='username']", username)
        page.fill("input[name='password']", password)
        page.click("button[type='submit']")
        
        print("Waiting for login to complete (handle 2FA in browser if needed)...")
        
        # Wait up to 5 minutes for user to complete 2FA
        # We check periodically for the 'Home' icon which signifies success
        for _ in range(60): # 60 * 5s = 300s = 5 mins
            if page.is_visible("svg[aria-label='Home']"):
                print("Login successful.")
                return True
                
            # Optional: Check for 2FA specific elements to give better feedback
            if page.is_visible("input[name='verificationCode']"):
                print(" -> 2FA prompt detected. Please enter the code in the browser.", end='\r')
            
            time.sleep(5)
            
        print("Login timed out. Did not detect 'Home' screen.")
        return False
    except Exception as e:
        print(f"Login process error: {e}")
        return False

def process_profile(page, profile_url):
    """
    Navigates to profile and performs actions logic.
    Returns the status string.
    """
    try:
        print(f"Processing: {profile_url}")
        page.goto(profile_url)
        time.sleep(2) # Short wait for page load

        # 6.1 Not Available Check
        # "Profile isn't available. The link may be broken, or the profile may have been removed."
        # Using a broad text search for "Profile isn't available" or "Sorry, this page isn't available."
        
        content = page.content()
        if "Sorry, this page isn't available." in content or "Profile isn't available" in content:
            print(" -> Profile not found.")
            return Status_NotFound

        # 7.1 Check "Following" button
        # Determining selectors for "Following", "Follow", "Follow Back" is tricky as they change.
        # We will look for buttons with specific text.
        
        # Logic Priority:
        # 1. Check if we are "Following" (User request says: "Click 'Following' button")
        #    This implies we start by looking for a button that says "Following".
        
        # NOTE: Instagram UI varies. 
        # "Following" button usually has text "Following".
        # "Follow Back" button usually has text "Follow Back".
        # "Follow" button usually has text "Follow".
        
        following_btn = page.locator("button:has-text('Following')")
        follow_back_btn = page.locator("button:has-text('Follow Back')")
        follow_btn = page.locator("button:has-text('Follow')")

        if following_btn.is_visible():
            print(" -> Detected 'Following' state. Clicking 'Following' content...")
            following_btn.click()
            
            # Handle "Unfollow" popup
            # User request: click "Following" -> popup -> click "Unfollow" -> wait for state change
            try:
                print(" -> Waiting for 'Unfollow' popup...")
                # The popup is often a list of divs. Searching by text is more robust than tag specific.
                # We target the dialog specifically if possible, or just the text 'Unfollow' visible on page.
                
                # Wait for the menu to appear
                page.locator("div[role='dialog']").wait_for(state="visible", timeout=5000)
                
                # Click the "Unfollow" text inside the dialog
                unfollow_btn = page.locator("div[role='dialog']").get_by_text("Unfollow", exact=True)
                if not unfollow_btn.is_visible():
                     # Fallback: sometimes text is slightly different or capitalized?
                     unfollow_btn = page.locator("div[role='dialog']").get_by_text("Unfollow")
                
                unfollow_btn.click()
                print(" -> Clicked 'Unfollow' in popup.")
                
                # IMPORTANT: Sometimes Instagram asks for DOUBLE confirmation (confirmation dialog)
                # If another dialog appears with "Unfollow" (often red), click it.
                # We give it a short moment to appear
                try:
                    confirm_unfollow = page.locator("button:has-text('Unfollow')") # The confirm button IS usually a button
                    if confirm_unfollow.is_visible(timeout=2000):
                        print(" -> Detected confirmation dialog. Clicking confirm...")
                        confirm_unfollow.click()
                except:
                    pass # No confirmation dialog, assumed done
                    
            except Exception as e:
                print(f" -> 'Unfollow' popup interaction failed: {e}")
                # Try fallback: maybe it's not in a dialog?
                try:
                   page.get_by_text("Unfollow").click(timeout=3000)
                   print(" -> Clicked 'Unfollow' using global text fallback.")
                except:
                   pass

            print(" -> Waiting for button state change to 'Follow' or 'Follow Back'...")
            # Wait for the button text to change from "Following" to "Follow" or "Follow Back"
            # We use regex to match exactly "Follow" or "Follow Back", explicitly excluding "Following".
            try:
                # This locator targets a button that strictly matches "Follow" or "Follow Back"
                page.locator("button").filter(has_text=re.compile(r"^(Follow|Follow Back)$")).first.wait_for(state="visible", timeout=15000)
                print(" -> State change detected.")
            except Exception as e:
                print(f" -> Warning: Wait for state change timed out (might still be 'Following' or broken UI). Continuing to check...")

            # 7.2 Check resulting state
            # Re-query buttons as DOM might have refreshed
            # IMPORTANT: Check "Follow Back" BEFORE "Follow" because "Follow" matches both.
            # Or use exact=True for strictness.
            
            # User requirement: If button changes to "Follow Back", click it.
            if page.locator("button:has-text('Follow Back')").is_visible():
                print(" -> State changed to 'Follow Back'. Clicking it...")
                page.locator("button:has-text('Follow Back')").click()
                
                # Verify it changes back to Following
                try:
                    page.locator("button:has-text('Following')").wait_for(state="visible", timeout=10000)
                    print(" -> State changed to 'Following'. Status: Following")
                    return Status_Following
                except:
                    print(" -> Failed to confirm 'Following' state after 'Follow Back'.")
                    return Status_Error

            elif page.get_by_text("Follow", exact=True).is_visible():
                 # Use strict match to ensure we don't accidentally match "Follow Back" or "Following"
                 # but "Following" is usually handled by other checks.
                 # Actually, "Follow" button usually checks text "Follow".
                 print(" -> State changed to 'Follow'. Status: UnFollowed")
                 return Status_UnFollowed
                 
            else:
                 # Check if it is still "Following" (meaning unfollow failed or cancelled)
                 if page.locator("button:has-text('Following')").is_visible():
                     print(" -> State remained 'Following'. (Unfollow failed?)")
                     return Status_Error
                 
                 print(" -> Unexpected state after clicking 'Following' and popup.")
                 return Status_Error

        elif follow_back_btn.is_visible():
             print(" -> 'Follow Back' button found immediately.")
             # Requirement: Click "Follow Back" -> Verify "Following"
             print(" -> Clicking 'Follow Back'...")
             follow_back_btn.click()
             
             try:
                 page.locator("button:has-text('Following')").wait_for(state="visible", timeout=10000)
                 print(" -> State changed to 'Following'. Status: Following")
                 return Status_Following
             except:
                 print(" -> Failed to confirm 'Following' state after initial 'Follow Back' click.")
                 return Status_Error
             
        else:
            print(" -> No recognizable relationship button found.")
            return Status_Error

    except Exception as e:
        print(f"Error processing profile: {e}")
        return Status_Error

def main():
    print("--- Instagram Follow-Back Processor ---")
    
    csv_path = input("Enter path to input CSV: ")
    if not os.path.exists(csv_path):
        print("File not found.")
        return

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Check columns
    required_cols = ["Username", "Instagram Link", "Date Followed"]
    if not all(col in df.columns for col in required_cols):
        print(f"CSV missing required columns: {required_cols}")
        return

    # Add Status column if not exists
    if "Status" not in df.columns:
        df["Status"] = ""

    user_data_dir = os.path.join(os.getcwd(), "instagram_user_data")
    print(f"Using browser profile at: {user_data_dir}")

    with sync_playwright() as p:
        # Use a persistent context to save cookies/session
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False
        )
        
        try:
            # Persistent context usually has one page open by default
            if len(browser.pages) > 0:
                page = browser.pages[0]
            else:
                page = browser.new_page()

            # Navigate to Instagram to check login state
            print("Checking login state...")
            page.goto("https://www.instagram.com/")
            time.sleep(3)
            
            is_logged_in = False
            # Check for Home icon
            try:
                if page.locator("svg[aria-label='Home']").is_visible(timeout=5000):
                    print("Already logged in.")
                    is_logged_in = True
            except:
                pass
                
            if not is_logged_in:
                print("Not checked in. Credentials required.")
                username = input("Enter Instagram Username: ")
                password = getpass.getpass("Enter Instagram Password: ")
                
                if not login_to_instagram(page, username, password):
                    print("Critical: Login failed.")
                    browser.close()
                    return
            
            # 4.1 Row Processing Flow
            for index, row in df.iterrows():
                # Skip if already processed? User didn't specify, but helpful. 
                # Requirements say "process rows top-to-bottom".
                
                link = row["Instagram Link"]
                user_handle = row["Username"]
                
                print(f"\n[{index+1}/{len(df)}] Processing {user_handle}...")
                
                status = process_profile(page, link)
                
                # Update DataFrame
                df.at[index, "Status"] = status
                
                # Save progress (Idempotence helper)
                output_file = csv_path.replace(".csv", "_updated.csv")
                try:
                    df.to_csv(output_file, index=False)
                    print(f"Saved progress to {output_file}")
                except Exception as e:
                    print(f"Error saving CSV: {e}")

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            try:
                browser.close()
            except Exception:
                pass # Suppress errors during close (e.g. if already closed)
            print("\nDate processing complete.")

if __name__ == "__main__":
    main()
