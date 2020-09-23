import time
from os import environ
from os.path import isdir
from traceback import print_exc, format_exc

import telegram
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException


def notify(message: str):
    token = environ.get('TELEGRAM_TOKEN')
    if not token:
        return
    chat_id = environ.get('TELEGRAM_CHAT_ID')
    if not chat_id:
        return
    bot = telegram.Bot(token)
    bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True,
                     parse_mode=telegram.ParseMode.MARKDOWN)


def send_keys_slow(el, text, delay=0.1):
    for c in text:
        el.send_keys(c)
        time.sleep(delay)


def do_magic():
    login = environ['LOGIN']
    password = environ['PASSWORD']
    host = environ.get('SELENIUM_HOST', 'selenium')

    driver = webdriver.Remote(command_executor='http://%s:4444/wd/hub' % host,
                              desired_capabilities=DesiredCapabilities.CHROME)
    try:
        driver.set_window_size(1440, 900)
        driver.get('https://www.boots.com/webapp/wcs/stores/servlet/BootsLogonForm')
        login_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//form[@id="gigya-login-form"]//input[@name="username"]'))
        )

        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//button[@title="Accept cookies"]')))
        cookie_btn = driver.find_element_by_xpath('//button[@title="Accept cookies"]')
        cookie_btn.click()

        send_keys_slow(login_input, login)
        send_keys_slow(driver.find_element_by_xpath('//form[@id="gigya-login-form"]//input[@name="password"]'), password)

        btn = driver.find_element_by_xpath('//form[@id="gigya-login-form"]//input[@type="submit"]')
        btn.click()

        WebDriverWait(driver, 10).until(EC.staleness_of(btn))
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//a[text()="personal information"]'))
        )

        driver.get('https://www.boots.com/webapp/wcs/stores/servlet/DigitalJustForMeView')
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//h2[text()="Offers just for me"]'))
        )

        offers = driver.find_elements_by_xpath('//ul[@id="offers_available"]/li/div[.//a[@title="Load to Advantage Card"]]')

        if offers:
            print('Found offers: %d' % len(offers))

            for offer in offers:
                promo_info = offer.find_element_by_xpath('.//div[@class="promotion_info"]')
                title = promo_info.find_element_by_xpath('./div[@class="promotions_points"]/a').text
                conditions = promo_info.find_element_by_xpath('./div[@class="promotions_condition"]/p').text
                validity = promo_info.find_element_by_xpath('./div[@class="promotions_expiry"]/p').text

                print('%s %s... ' % (title, conditions), end='')

                btn = promo_info.find_element_by_xpath('.//div[@class="promotions_add"]/a[@title="Load to Advantage Card"]')
                btn.click()
                WebDriverWait(driver, 15).until(EC.invisibility_of_element(btn))
                print('saved')

                notify('Boots offer saved — %s %s (%s)' % (title, conditions, validity))
                WebDriverWait(driver, 15).until(EC.invisibility_of_element(btn))
    except WebDriverException:
        print_exc()
        notify('Exception from Boots saver: \n```\n' + format_exc() + '\n```')
        if isdir('./screenshots'):
            filename = './screenshots/%d.png' % time.time()
            s = lambda X: driver.execute_script('return document.body.parentNode.scroll'+X)
            driver.set_window_size(s('Width'), s('Height'))
            driver.find_element_by_tag_name('body').screenshot(filename)

            print('Got exception! Screenshot saved to %s' % filename)
    finally:
        driver.quit()


if __name__ == '__main__':
    while True:
        do_magic()
        sleep = int(environ.get('RESTART_DELAY', 0))
        if sleep > 0:
            time.sleep(sleep)
        else:
            break
