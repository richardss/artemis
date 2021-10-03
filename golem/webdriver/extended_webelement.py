from typing import List
import time

from selenium.webdriver.remote.webelement import WebElement as RemoteWebElement
from selenium.webdriver.firefox.webelement import FirefoxWebElement
from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select as SeleniumSelect
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

from golem.webdriver.common import _find, _find_all
from golem.webdriver import golem_expected_conditions as gec


class ExtendedWebElement:

    selector_type = None
    selector_value = None
    name = None

    def check(self):
        """Check element if element is checkbox or radiobutton.
        If element is already checked, this is ignored.
        """
        checkbox_or_radio = (self.tag_name == 'input' and
                             self.get_attribute('type') in ['checkbox', 'radio'])
        if checkbox_or_radio:
            if not self.is_selected():
                self.click()
        else:
            raise ValueError(f'Element {self.name} is not checkbox or radiobutton')

    def double_click(self):
        """Double click the element"""
        action_chains = ActionChains(self.parent)
        action_chains.double_click(self).perform()

    def find(self, element=None, id=None, name=None, link_text=None,
             partial_link_text=None, css=None, xpath=None, tag_name=None,
             timeout=None, wait_displayed=None, highlight=None) -> 'ExtendedRemoteWebElement':
        """Find a WebElement

        Search criteria:
        The first argument must be: an element tuple, a CSS string,
        an XPath string, or a WebElement object.
        Keyword search criteria: id, name, link_text, partial_link_text,
        css, xpath, tag_name.
        Only one search criteria should be provided.

        Other args:
        - timeout: timeout (in seconds) to wait for element to be present.
                   by default it uses the *search_timeout* setting value
        - wait_displayed: wait for element to be displayed (visible).
                          by default uses the *wait_displayed* setting value

        :Usage:
            element.find('div#someId > input.class')
            element.find(('id', 'someId'))
            element.find(id='someId')
            element.find(xpath='//div/input', timeout=5, wait_displayed=True)

        :Returns:
          a golem.webdriver.extended_webelement.ExtendedRemoteWebElement
        """
        return _find(self, element, id, name, link_text, partial_link_text,
                     css, xpath, tag_name, timeout, wait_displayed, highlight)

    def find_all(self, element=None, id=None, name=None, link_text=None,
                 partial_link_text=None, css=None, xpath=None,
                 tag_name=None) -> List['ExtendedRemoteWebElement']:
        """Find all WebElements that match the search criteria.

        Search criteria:
        The first argument must be: an element tuple, a CSS string, or
        an XPath string.
        Keyword search criteria: id, name, link_text, partial_link_text,
        css, xpath, tag_name.
        Only one search criteria should be provided.

        :Usage:
            element.find_all('div#someId > span.class')
            element.find(('tag_name', 'input'))
            element.find(xpath='//div/input')

        :Returns:
            a list of ExtendedRemoteWebElement
        """
        return _find_all(self, element, id, name, link_text, partial_link_text, css,
                         xpath, tag_name)

    def focus(self):
        """Give focus to element"""
        self.parent.execute_script('arguments[0].focus();', self)

    def has_attribute(self, attribute):
        """Returns whether element has attribute"""
        return self.get_attribute(attribute) is not None

    def has_focus(self):
        """Returns whether element has focus"""
        script = 'return arguments[0] == document.activeElement'
        return self.parent.execute_script(script, self)

    def highlight(self):
        """Highlight element"""
        try:
            self.parent.execute_script(HIGHLIGHT_ELEMENT_SCRIPT, self)
        except Exception as e:
            pass

    @property
    def inner_html(self):
        """"Element innerHTML attribute"""
        return self.get_attribute('innerHTML')

    def javascript_click(self):
        """Click element using Javascript"""
        self.parent.execute_script('arguments[0].click();', self)

    def mouse_over(self):
        """Mouse over element"""
        action_chains = ActionChains(self.parent)
        action_chains.move_to_element(self).perform()

    @property
    def outer_html(self):
        """"Element outerHTML attribute"""
        return self.get_attribute('outerHTML')

    def press_key(self, key):
        """Press a key on element

        :Usage:
          element.press_key('ENTER')
          element.press_key('TAB')
          element.press_key('LEFT')
        """
        if hasattr(Keys, key):
            key_attr = getattr(Keys, key)
            self.send_keys(key_attr)
        else:
            defined_keys = [name for name in dir(Keys) if not name.startswith('_')]
            error_msg = (f'Key {key} is invalid\n'
                         'valid keys are:\n'
                         f'{",".join(defined_keys)}')
            raise ValueError(error_msg)

    @property
    def select(self):
        """Return a Select object"""
        return Select(self)

    def send_keys_with_delay(self, value, delay=0.1):
        """Send keys to element one by one with a delay between keys.

        :Args:
         - value: a string to type
         - delay: time between keys (in seconds)

        :Raises:
         - ValueError: if delay is not a positive int or float
        """
        if not isinstance(delay, int) and not isinstance(delay, float):
            raise ValueError('delay must be int or float')
        elif delay < 0:
            raise ValueError('delay must be a positive number')
        else:
            for c in value:
                self.send_keys(c)
                time.sleep(delay)

    def uncheck(self):
        """Uncheck element if element is checkbox.
        If element is already unchecked, this is ignored.
        """
        is_checkbox = (self.tag_name == 'input' and
                       self.get_attribute('type') == 'checkbox')
        if is_checkbox:
            if self.is_selected():
                self.click()
        else:
            raise ValueError(f'Element {self.name} is not checkbox')

    @property
    def value(self):
        """The value attribute of element"""
        return self.get_attribute('value')

    def wait_displayed(self, timeout=30):
        """Wait for element to be displayed

        :Returns:
          The element
        """
        wait = WebDriverWait(self.parent, timeout)
        message = f'Timeout waiting for element {self.name} to be displayed'
        wait.until(ec.visibility_of(self), message=message)
        return self

    def wait_enabled(self, timeout=30):
        """Wait for element to be enabled

        :Returns:
          The element
        """
        wait = WebDriverWait(self.parent, timeout)
        message = f'Timeout waiting for element {self.name} to be enabled'
        wait.until(gec.element_to_be_enabled(self), message=message)
        return self

    def wait_has_attribute(self, attribute, timeout=30):
        """Wait for element to have attribute

        :Returns:
          The element
        """
        wait = WebDriverWait(self.parent, timeout)
        message = f'Timeout waiting for element {self.name} to have attribute {attribute}'
        wait.until(gec.element_to_have_attribute(self, attribute), message=message)
        return self

    def wait_has_not_attribute(self, attribute, timeout=30):
        """Wait for element to not have attribute

        :Returns:
          The element
        """
        wait = WebDriverWait(self.parent, timeout)
        message = f'Timeout waiting for element {self.name} to not have attribute {attribute}'
        wait.until_not(gec.element_to_have_attribute(self, attribute),
                       message=message)
        return self

    def wait_not_displayed(self, timeout=30):
        """Wait for element to be not displayed

        :Returns:
          The element
        """
        wait = WebDriverWait(self.parent, timeout)
        message = f'Timeout waiting for element {self.name} to be not displayed'
        wait.until_not(ec.visibility_of(self), message=message)
        return self

    def wait_not_enabled(self, timeout=30):
        """Wait for element to be not enabled

        :Returns:
          The element
        """
        wait = WebDriverWait(self.parent, timeout)
        message = f'Timeout waiting for element {self.name} to be not enabled'
        wait.until_not(gec.element_to_be_enabled(self), message=message)
        return self

    def wait_text(self, text, timeout=30):
        """Wait for element text to match given text

        :Returns:
          The element
        """
        wait = WebDriverWait(self.parent, timeout)
        message = f"Timeout waiting for element {self.name} text to be '{text}'"
        wait.until(gec.element_text_to_be(self, text), message=message)
        return self

    def wait_text_contains(self, text, timeout=30):
        """Wait for element to contain given text

        :Returns:
          The element
        """
        wait = WebDriverWait(self.parent, timeout)
        message = f"Timeout waiting for element {self.name} text to contain '{text}'"
        wait.until(gec.element_text_to_contain(self, text), message=message)
        return self

    def wait_text_is_not(self, text, timeout=30):
        """Wait fo element text to not match given text

        :Returns:
          The element
        """
        wait = WebDriverWait(self.parent, timeout)
        message = f"Timeout waiting for element {self.name} text not to be '{text}'"
        wait.until_not(gec.element_text_to_be(self, text), message=message)
        return self

    def wait_text_not_contains(self, text, timeout=30):
        """Wait for element text to not contain text

        :Returns:
          The element
        """
        wait = WebDriverWait(self.parent, timeout)
        message = f"Timeout waiting for element {self.name} text to not contain '{text}'"
        wait.until_not(gec.element_text_to_contain(self, text),
                       message=message)
        return self


class Select(SeleniumSelect):

    @property
    def first_selected_option(self):
        """Return the first selected option as a
        Golem ExtendedWebElement"""
        option = super(Select, self).first_selected_option
        return extend_webelement(option)


class ExtendedRemoteWebElement(RemoteWebElement, ExtendedWebElement):
    pass


class ExtendedFirefoxWebElement(FirefoxWebElement, ExtendedWebElement):
    pass


def extend_webelement(web_element) -> ExtendedRemoteWebElement:
    """Extend the selenium WebElement using the
    ExtendedRemoteWebElement or ExtendedFirefoxWebElement class
    """
    if isinstance(web_element.parent, FirefoxDriver):
        web_element.__class__ = ExtendedFirefoxWebElement
    else:
        web_element.__class__ = ExtendedRemoteWebElement
    return web_element


HIGHLIGHT_ELEMENT_SCRIPT = """
	let boundingRect = arguments[0].getBoundingClientRect();
	boundingRect.left = boundingRect.left + window.scrollX;
	boundingRect.top = boundingRect.top + window.scrollY;
	if(isNaN(boundingRect.width)) {
		boundingRect.width = 0;
	}
	if(isNaN(boundingRect.height)) {
		boundingRect.height = 0;
	}
	
	let borders = {
		top: document.createElement('div'),
		left: document.createElement('div'),
		right: document.createElement('div'),
		bottom: document.createElement('div'),
	}

	Object.keys(borders).forEach(border => {
		borders[border].style.position = 'absolute';
		borders[border].style.backgroundColor = 'yellow';
	});

	borders.top.style.left = boundingRect.left - 5 + 'px';
	borders.top.style.top = boundingRect.top - 5 + 'px';
	borders.top.style.width = boundingRect.width + 10 + 'px';
	borders.top.style.height = '4px';

	borders.left.style.left = boundingRect.left - 5 + 'px';
	borders.left.style.top = boundingRect.top - 5 + 'px';
	borders.left.style.height = boundingRect.height + 10 + 'px';
	borders.left.style.width = '4px';

	borders.right.style.left = boundingRect.left + boundingRect.width + 1 + 'px';
	borders.right.style.top = boundingRect.top - 5 + 'px';
	borders.right.style.height = boundingRect.height + 10 + 'px';
	borders.right.style.width = '4px';

	borders.bottom.style.left = boundingRect.left - 5 + 'px';
	borders.bottom.style.top = boundingRect.top + boundingRect.height + 1 + 'px';
	borders.bottom.style.width = boundingRect.width + 10 + 'px';
	borders.bottom.style.height = '4px';

	let zIndex = parseInt(arguments[0].style.zIndex);
	if(!Number.isNaN(zIndex)) {
		Object.keys(borders).forEach(border => borders[border].style.zIndex = zIndex + 1);
	}
	Object.keys(borders).forEach(border => document.body.appendChild(borders[border]));
	
	setTimeout(() => {
		Object.keys(borders).forEach(border => borders[border].style.backgroundColor = 'transparent');
	}, 300);
	setTimeout(() => {
		Object.keys(borders).forEach(border => borders[border].style.backgroundColor = 'yellow');
	}, 600);
	setTimeout(() => {
		Object.keys(borders).forEach(border => borders[border].remove());
	}, 900);"""