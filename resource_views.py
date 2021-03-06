# -*- coding: UTF-8 -*-
# Copyright (C) 2010 Norman Khine <norman@khine.net>

# Import from the Standard Library
import datetime, random, hashlib, subprocess, urllib
from random import choice, sample
from operator import itemgetter

# Import from PIL
import Image, ImageFont, ImageDraw, ImageFilter

# Import from itools
from itools.core import get_abspath
from itools.core import freeze
from itools.datatypes import Boolean, Email, Integer, String, Unicode
from itools.gettext import MSG
from itools.handlers import checkid
from itools.stl import stl
from itools.uri import get_reference, get_uri_path
from itools.web import STLView, INFO, ERROR, STLForm, get_context
from itools.xml import XMLParser

# Import from ikaaro
from ikaaro.autoform import Widget, ProgressBarWidget as BaseProgressBarWidget
from ikaaro.autoform import title_widget, make_stl_template
from ikaaro.datatypes import Password, Multilingual
from ikaaro.resource_views import LoginView as BaseLoginView
#from ikaaro.utils import generate_password
from ikaaro.views import CompositeForm
from ikaaro.views import IconsView, SearchForm, ContextMenu
from ikaaro.utils import CMSTemplate


from ikaaro.table import OrderedTable, OrderedTableFile
from ikaaro.table_views import OrderedTable_View, Table_EditRecord

# Import from here
from tzm.datatypes import getCountries, getRegions, getCounties
from tzm.datatypes import sort_key
from tzm.utils import gravatar_url

fonts = ['data/fonts/tesox.ttf', 'data/fonts/SHERWOOD.TTF']

def crypt_captcha(captcha):
    return hashlib.sha224(captcha).hexdigest()

def get_host_prefix(context):
    hostname = context.uri.authority
    tab = hostname.split('.', 1)
    if len(tab)>1:
        return tab[0]
    return None
#
# ASCII letters and digits, except the characters: 0, O, 1, l, w, W
tokens = 'abcdefghijkmnopqrstuvxyzABCDEFGHIJKLMNPQRSTUVXYZ23456789'
def generate_password(length=5):
    return ''.join(sample(tokens, length))

class Captcha(STLView):
    """
    Ajax'ed driven widget.
    """
    access = True
    template = 'ui/core/templates/widgets/captcha.xml'

    def get_captcha(self, resource, context):
        referrer = context.get_referrer()
        # Build the namespace
        namespace = {}
        # Captcha
        # create a 5 char random strin
        imgtext = generate_password(5)
        crypt_imgtext = crypt_captcha(imgtext)
        encoded_imgtext = Password.encode('%s' % crypt_imgtext)
        # randomly select the foreground color
        fgcolor = random.randint(0,0xffff00)
        # make the background color the opposite of fgcolor
        bgcolor = fgcolor ^ 0xffffff    
        #path = get_abspath('data/images/bg.jpg')
        #im=PILImage.open(path)
        font_path = get_abspath(choice(fonts))
        font=ImageFont.truetype(font_path, 38)
        dim = font.getsize(imgtext)
        # create a new image slightly larger that the text
        im = Image.new('RGB', (dim[0]+5,dim[1]+5), bgcolor)
        d = ImageDraw.Draw(im)
        # draw 100 random colored boxes on the background
        x, y = im.size
        r = random.randint
        for num in range(100):
            d.rectangle((r(0,x),r(0,y),r(0,x),r(0,y)),fill=r(0,0xffffff))
        d.text((3,3), imgtext, font=font, fill=fgcolor)
        im = im.filter(ImageFilter.EDGE_ENHANCE_MORE)
        # save as a temporary image
        # FIXME on page refresh the first file is not removed.
        im_name = generate_password(38)
        SITE_IMAGES_DIR_PATH = get_abspath('ui/core/captcha/images')
        tempname = '%s/%s' % (SITE_IMAGES_DIR_PATH, (im_name + '.jpg'))
        im.save(tempname, "JPEG")
        path = get_abspath(tempname)
        img = resource.get_handler()
        namespace['img'] = img
        captcha = '/ui/core/captcha/images/%s' % (im_name + '.jpg')
        namespace['captcha'] = captcha

        # we need to pass this path as we can then delete the captcha file
        namespace['captcha_path'] = 'ui/images/captcha/%s' % (im_name + '.jpg')
        namespace['crypt_imgtext'] = encoded_imgtext
        namespace['get-captcha'] = 'ui/core/captcha/captcha.xml.en'
        # Generate a sound file of the captcha
        sound_path = get_abspath('data/sound')
        SOUND_OUTPUT_PATH = get_abspath('ui/core/captcha/sounds')
        sox_filenames = []
        for x in imgtext:
            if x.isupper():
                sox_filenames.append('%s/upper_%s.wav' % (sound_path, \
                                    x.lower()))
            else:
                sox_filenames.append('%s/%s.wav' % (sound_path, x))
        #
        subprocess.call(['sox'] + sox_filenames + \
                ['%s/%s' % (SOUND_OUTPUT_PATH, (im_name + '.mp3'))])
        namespace['sound_captcha'] = '/ui/core/captcha/sounds/%s' % (im_name + '.mp3')
        namespace['sound_path'] = 'ui/sound/%s' % (im_name + '.mp3')

        return namespace
        
    def get_namespace(self, resource, context):
        context.set_content_type('text/html')
        namespace = self.get_captcha(resource, context)

        return namespace

class LoginView(BaseLoginView):
    access = True
    title = MSG(u'Zeitgeist Global Connect Login')
    template = 'ui/core/templates/forms/login.xml'
    meta = [('robots', 'noindex, follow', None)]

    schema = {
        'username': String(mandatory=True),
        'password': String,
        'captcha': String,
        'crypt_imgtext': String,
        'no_password': Boolean}

    def get_namespace(self, resource, context):
        namespace = super(LoginView, self).get_namespace(resource, context)
        namespace['register'] = context.site_root.is_allowed_to_register()
        namespace['captcha'] = Captcha().get_captcha(resource, context)

        return namespace

    def _register(self, resource, context, email):
        site_root = context.site_root
        # Add the user
        users = site_root.get_resource('users')
        user = users.set_user(email, None)
        # Set the role to 'Member'
        default_role = site_root.class_roles[1]
        site_root.set_user_role(user.name, default_role)

        # Send confirmation email
        user.send_confirmation(context, email)

        # Bring the user to the login form
        message = MSG(
            u"An email has been sent to you, to finish the registration "
            u"process follow the instructions detailed in it.")
        return message.gettext().encode('utf-8')

    def action(self, resource, context, form):
        # Get the user
        email = form['username'].strip()
        user = context.root.get_user_from_login(email)
        if form['no_password']:
            if not Email.is_valid(email):
                message = u'The given username is not an email address.'
                context.message = ERROR(message)
                return
            # Case 1: Register
            # check captcha first
            captcha = form['captcha'].strip()
            crypted = crypt_captcha(captcha)
            crypt_imgtext = form['crypt_imgtext'].strip()
            decrypt =  Password.decode('%s' % crypt_imgtext)
            if crypted != decrypt:
                error = u"You typed an incorrect captcha string."
                context.message = ERROR(error)
                return
            # does the user exists?
            if user is None:
                if context.site_root.is_allowed_to_register():
                    return self._register(resource, context, email)
                    # FIXME This message does not protect privacy
                    error = u"You don't have an account, contact the site admin."
                    context.message = ERROR(error)
                    return
            # Case 2: Forgotten password
            email = user.get_property('email')
            user.send_forgotten_password(context, email)
            path = '/ui/website/forgotten_password.xml'
            handler = resource.get_resource(path)
            return stl(handler)
        
        # Case 3: Login
        password = form['password']
        if user is None or not user.authenticate(password, clear=True):
            context.message = ERROR(u'The email or the password is incorrect.')
            return
        # Set cookie & context
        user.set_auth_cookie(context, password)
        context.user = user

        # Come back
        referrer = context.get_referrer()
        if referrer is None:
            goto = get_reference('./')
        else:
            path = get_uri_path(referrer)
            if path.endswith(';login'):
                goto = get_reference('./')
            else:
                goto = referrer
        return context.come_back(INFO(u"Welcome to the Phoenix Project!"), goto)


class RegionSelect(Widget):

    """
    We return Country/Region/County list for non javascrip enabled browsers.
    """
    template = make_stl_template("""
        <fieldset>
            <select id="${ids}" name="${ids}">
                <option stl:repeat="option options" value="${option/name}" selected="${option/selected}">
                    ${option/value}
                </option>
            </select>
        </fieldset>
    """)

    @classmethod
    def options(cls):
        selected = True
        context = get_context()
        ids_form_value =  context.get_form_value('county') or context.get_form_value('region') \
                            or context.get_form_value('country')

        if ids_form_value:
            ids_form_value = ids_form_value.rsplit('#')
            if len(ids_form_value) == 1:
                if ids_form_value[-1] == 'switch':
                    options = getCountries().get_options()
                    has_empty_value = 'Select your country'
                else:
                    options = getRegions().get_options(ids_form_value[0])
                    has_empty_value = 'Select your region'
            else:
                if ids_form_value[-1] == 'switch':
                    options = getRegions().get_options(ids_form_value[0])
                    has_empty_value = 'Select your region'
                else:
                    ''' here we return iana_root_zone#country#region'''
                    if len(ids_form_value) == 3:
                        ''' if there is an error on the form, we need to remember the value the user has added!'''
                        options = getCounties().get_options(ids_form_value[0], ids_form_value[1], ids_form_value[2])
                    else:
                        options = getCounties().get_options(ids_form_value[0], ids_form_value[1])
                    has_empty_value = 'Select your county'
        else:
            options = getCountries().get_options()
            has_empty_value = 'Select your country'

        if cls.has_empty_option:
            options.insert(0,
                {'name': '', 'value': has_empty_value, 'selected': selected})


        return options

    @classmethod
    def ids(self):
        context = get_context()
        ids_form_value = context.get_form_value('county') or context.get_form_value('region') \
                or context.get_form_value('country') or get_host_prefix(context)

        if ids_form_value:
            ids_form_value = ids_form_value.rsplit('#')
            if len(ids_form_value) == 1:
                if ids_form_value[0] == 'switch':
                    return 'country'
                else:
                    return 'region'
            else:
                if ids_form_value[-1] == 'switch':
                    return 'region'
                else:
                    return 'county'
        else:
            return 'country'

class ProgressBarWidget(BaseProgressBarWidget):

    template = make_stl_template("""
    <div id ="progress-bar-widget">
        <div id="attachment-file-infos">
            <p id="file-name" />
            <p id="file-size" />
            <p id="file-type" />
        </div>
        <div id="progress-bar-box">
            <span><div id="progress-bar"/></span><span id="percent"/>
            <div id="upload-size" />
        </div>
    </div>
    <script type="text/javascript">
      $('head').append('<link rel="stylesheet" href="/ui/core/progressbar/jquery-progressbar.css" type="text/css" />');
      var upload_id = ${upload_id};
      $("INPUT:file").focus(function () {
        attachmentSelected($(this));
      });
    </script>
    <script  type="text/javascript" src="/ui/core/progressbar/jquery-progressbar.min.js"/>
    """)


class Chat(CMSTemplate):
    """
        Chat template, that links to a nodejs server running nowjs.
        We check if the user is logged in, and we return the user's name
        as a string which is then passed to the now.name object.
    """
    
    @classmethod
    def user(self):
        context = get_context()
        user = context.user
        if user:
            return user.get_firstname()
        return None

    @classmethod
    def path(self):
        context = get_context()
        user = context.user
        if user:
            # here we want to add a Private Message functionality
            return '/users/%s' % user.name
        return '/'

    @classmethod
    def server(self):
        context = get_context()
        hostname = context.uri.authority
        
        return hostname

    @classmethod
    def gravatar(self):
        gravatar_url
        context = get_context()
        user = context.user
        if user:
            email = user.get_property('email')
            return gravatar_url(email)
        return None

    template = 'ui/core/templates/widgets/chat.xml'

    # we need to store the messages so that on page refresh they are listed!

class Message_TableHandler(OrderedTableFile):
    
    record_properties = {'title': Multilingual(mandatory=True)}
 
 
class Messages_TableResource(OrderedTable):

    class_id = 'messages_select_table'
    class_title = MSG(u'Select Table')
    class_handler = Message_TableHandler

    # Hide in browse_content
    is_content = False

    form = [title_widget]


    def get_options(self, value=None, sort=None):
        # Find out the options
        handler = self.handler
        options = []
        for id in handler.get_record_ids_in_order():
            record = handler.get_record(id)
            title = handler.get_record_value(record, 'title')
            options.append({'id': id, 'title': title})

        # Sort
        if sort is not None:
            options.sort(key=lambda x: x.get(sort))

        # Set 'is_selected'
        if value is None:
            for option in options:
                option['is_selected'] = False
        elif isinstance(value, list):
            for option in options:
                option['is_selected'] = (option['id'] in value)
        else:
            for option in options:
                option['is_selected'] = (option['id'] == value)

        return options


    #view = SelectTable_View()
    #edit_record = SelectTable_EditRecord()

class Map(STLView):
	
	access = True
	title = MSG(u'Map')
	template = 'ui/core/templates/pages/map.xml'
	
	scripts = ['/faye.js',
		'/ui/core/js/d3/d3.v2.min.js',
		'/ui/core/js/raphaeljs/raphael-min.js',
		'/ui/core/js/node/public/fisheye.js',
		'/ui/core/js/node/public/client.js'
	]