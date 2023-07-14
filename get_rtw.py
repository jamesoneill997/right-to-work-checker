from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

class RightToWork:
    STATUS_ACCEPTED = 0
    STATUS_REJECTED = 1
    STATUS_NOT_FOUND = 2
    def __init__(self, share_code, dob):
        self.share_code = share_code
        self.dob = self.get_dob(dob)
        self.chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
        
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument("--disable-dev-shm-usage") #disable shared memory on Heroku
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")

        self.driver = webdriver.Chrome(service=Service(self.chromedriver_path), options=self.chrome_options)
        self.status = self.get_rtw_status()
        
    def get_dob(self, dob):
        dob_formatted = {
            "day": dob.split('-')[0],
            "month": dob.split('-')[1],
            "year": dob.split('-')[2]
        }
        return dob_formatted
        
    def get_rtw_status(self):
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

        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "kc-container")))
        
        result = self.driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[1]/h1')
        return result.text