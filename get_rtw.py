from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException
)
from datetime import datetime
from webdriver_manager.chrome import ChromeDriverManager

import os
import re

class RightToWork:
    STATUS_ACCEPTED = "ACCEPTED"
    STATUS_REJECTED = "REJECTED"
    STATUS_NOT_FOUND = "NOT_FOUND"
    def __init__(self, share_code, dob, forename, surname, company_name=None):
        self.share_code = share_code
        self.forename = forename
        self.surname = surname
        self.dob = self.get_dob(dob)
        self.rejected_reasons = {
            "sponsor": "SPONSORSHIP",
            "student": "STUDENT",
        }
        if not company_name:
            self.company_name = os.environ.get("COMPANY_NAME") if "COMPANY_NAME" in os.environ else "Unknown"
        else:
            self.company_name = company_name
        self.chromedriver_path = os.environ.get("CHROMEDRIVER_PATH") if "CHROMEDRIVER_PATH" in os.environ else "./chromedriver"
        self.chrome_options = Options()
        if os.environ.get("ENV") == "production":
            self.chrome_options.add_argument('--headless') #headless mode on Heroku for speed, not needed for local dev as helps debugging
        self.chrome_options.add_argument("--disable-dev-shm-usage") #disable shared memory on Heroku
        self.chrome_options.add_argument("--no-sandbox")
        if "GOOGLE_CHROME_BIN" in os.environ:
            self.chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.chrome_options)
        self.status = self.get_rtw_status()
        
    def get_dob(self, dob):
        dob_formatted = {
            "day": dob.split('-')[0],
            "month": dob.split('-')[1],
            "year": dob.split('-')[2]
        }
        return dob_formatted
    
    def format_dates_from_details(self, text):
        date_pattern = r"(\d{1,2} \w+ \d{4})" 
        dates = re.findall(date_pattern, text)  
        formatted_dates = [datetime.strptime(date, "%d %B %Y").strftime("%d/%m/%Y") for date in dates]
        print(formatted_dates)
        return formatted_dates
        
    def get_rtw_status(self):
        if not self.forename or not self.surname or not self.dob or not self.share_code:
            result = {
                "outcome": self.STATUS_REJECTED,
                "rejected_reason": 'MISSING_DETAILS',
            }
            return result
        # Open the URL
        url = 'https://right-to-work.service.gov.uk/rtw-view'
        self.driver.get(url)
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.NAME, "shareCode")))

        # Find the shareCode input element and input a share code
        share_code_input = self.driver.find_element(By.NAME, 'shareCode')
        share_code_input.send_keys(self.share_code)

        submit_button = self.driver.find_element(By.ID, 'submit')
        submit_button.click()

        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "dob-day")))

        day_input = self.driver.find_element(By.ID, 'dob-day')
        month_input = self.driver.find_element(By.ID, 'dob-month')
        year_input = self.driver.find_element(By.ID, 'dob-year')

        day_input.send_keys(self.dob['day'])
        month_input.send_keys(self.dob['month'])
        year_input.send_keys(self.dob['year'])

        submit_button = self.driver.find_element(By.ID, 'submit')
        submit_button.click()
        try:
            WebDriverWait(self.driver, 2).until(EC.text_to_be_present_in_element((By.CLASS_NAME, "govuk-heading-xl"), "Details"))
            result = self.driver.find_element(By.XPATH, "//*[@id=\"main-content\"]/div/div[1]/h1")
                
        except TimeoutException: #share code found
            company_name_input = self.driver.find_element(By.ID, "checkerName")
            company_name_input.send_keys(self.company_name)
            submit_button = self.driver.find_element(By.XPATH, '//*[@id="gov-grid-row-content"]/div/form/input[1]')
            submit_button.click()
            try:
                WebDriverWait(self.driver, 6).until(EC.presence_of_element_located((By.ID, "profileImage")))
                
            except TimeoutException: #invalid share code
                page_heading = self.driver.find_element(By.XPATH, '//*[@id="gov-grid-row-content"]/div/form/h1').text
                if "problem" in page_heading.lower():
                    result = {
                        "outcome": self.STATUS_REJECTED,
                        "rejected_reason": 'SHARE_CODE_ERROR',
                    }
                    return result

            title = self.driver.find_element(By.XPATH, '//*[@id="gov-grid-row-content"]/div/form/div/div[1]/div[1]/h1').text
            name = self.driver.find_element(By.XPATH, '//*[@id="gov-grid-row-content"]/div/form/div/div[1]/div[2]/div[2]/h2').text
            details = self.driver.find_element(By.XPATH, '//*[@id="gov-grid-row-content"]/div/form/div/div[1]/div[2]/div[2]/p[1]').text
            dates = self.format_dates_from_details(details)
            if len(dates) == 1:
                start_date = datetime.today().strftime('%d/%m/%Y')
                expiry_date = dates[0]
            elif len(dates) == 2:
                start_date = dates[0]
                expiry_date = dates[1]
            else:
                start_date = datetime.today().strftime('%d/%m/%Y')
                expiry_date = None
            try:
                conditions = self.driver.find_element(By.XPATH, '//*[@id="gov-grid-row-content"]/div/form/div/div[1]/div[2]/div[2]/p[3]').text
            except Exception as e:
                conditions = "N/A"

            if self.forename.lower().strip() not in name.lower().strip() or self.surname.lower().strip() not in name.lower().strip():
                result = {
                    "outcome": self.STATUS_REJECTED,
                    "rejected_reason": 'NAME_MISMATCH',
                    "title":title,
                    "name": name,
                    "details": details,
                    "start_date":start_date,
                    "expiry_date":expiry_date,
                    "conditions":conditions,
                }
                return result
            for k, v in self.rejected_reasons.items():
                if k in conditions.lower():
                    result = {
                        "outcome": self.STATUS_REJECTED,
                        "rejected_reason": v,
                        "title":title,
                        "name": name,
                        "details": details,
                        "start_date":start_date,
                        "expiry_date":expiry_date,
                        "conditions":conditions,
                    }
                    return result
            result = {
                "outcome": self.STATUS_ACCEPTED,
                "title":title,
                "name": name,
                "details": details,
                "start_date":start_date,
                "expiry_date":expiry_date,
                "conditions":conditions,
            }
            return result
        
        return result.text