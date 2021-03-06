# -*- coding: UTF-8 -*-
# Copyright (C) 2011 Norman Khine <norman@khine.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


# Import from the Standard Library
import subprocess

# Import from itools
from itools.core import get_pipe
from itools.csv import CSVFile, Table
from itools.gettext import MSG
from itools.core import get_abspath
from itools.datatypes import Date, Integer, String, Unicode, URI

# Import from ikaaro
from ikaaro.folder_views import Folder_BrowseContent
from ikaaro.blog import Blog
from ikaaro.calendar import Calendar
from ikaaro.registry import register_resource_class
from ikaaro.revisions_views import DBResource_CommitLog
from ikaaro.root import Root as BaseRoot
from ikaaro.table import OrderedTable, OrderedTableFile
from ikaaro.table_views import OrderedTable_View, Table_EditRecord
from ikaaro.text import CSV
from ikaaro.tracker import Tracker

# Import from wiki
from wiki import WikiFolder

# Import from tzm
from chapter.chapter import Chapters
from phoenix.phoenix import Phoenix
from project.project import Projects
#from training.training import Training
from forums.forums import Forums

message_date = Date.decode('2003-10-23')
MESSAGES_DATA = """0, 0, 120124, 'hello world'"""
###########################################################################
# Resources
###########################################################################

class Affiliations(CSV):
    
    class_id = 'affiliations'
    def init_resource(self):
        super(Affiliations, self).init_resource()
        path =  get_abspath('data/affiliations.csv')
        self.handler.load_state_from_uri(path)

class Industry(CSV):
    
    class_id = 'industry'
    def init_resource(self):
        super(Industry, self).init_resource()
        path = get_abspath('data/industry.csv')
        self.handler.load_state_from_uri(path)

class Topics(CSV):
    
    class_id = 'topics'
    def init_resource(self):
        super(Topics, self).init_resource()
        path =  get_abspath('data/topics.csv')
        self.handler.load_state_from_uri(path)

class Types(CSV):
    
    class_id = 'types'
    def init_resource(self):
        super(Types, self).init_resource()
        path = get_abspath('data/types.csv')
        self.handler.load_state_from_uri(path)

class Functions(CSV):
    
    class_id = 'functions'
    def init_resource(self):
        super(Functions, self).init_resource()
        path =  get_abspath('data/functions.csv')
        self.handler.load_state_from_uri(path)

class World(CSV):
    
    class_id = 'world'
    class_csv_guess = True

    def init_resource(self):
        super(World, self).init_resource()
        path =  get_abspath('data/countries.csv')
        self.handler.load_state_from_uri(path)

class Messages(CSVFile):
    
    class_id = 'messages'
    class_version = '20111020'
    columns = ['user', 'users', 'timestamp', 'message']
    
    schema = {'user': Unicode,
              'users': Unicode,
              'timestamp': Unicode,
              'message': Unicode}


class Root(BaseRoot):
    """
        This is the root of the application and sets up the initial content.
        We create zmgc site and all the supporting content.
        The zmgc.net contains blog, calendar, forums, issue's tracker and wiki
        These will change in the future as these will have to also include data
        from other chapters and data sources.
        
        So simply this is your .ini file which sets up the application.
    """
    class_id = 'tzm'
    class_version = '20111020'
    class_title = MSG(u'Zeitgeist Application Server')
    class_description = MSG(u'One back-office to bring them all and in the'
                            u' darkness bind them, in an'
                            u' anarchically scalable information system.')

    def init_resource(self, email, password, admins=('0',)):
        # Create the root account
        super(Root, self).init_resource(email, password, admins=admins)
        # Load the static data files into the database
        affiliations = self.make_resource('affiliations', Affiliations)
        industry = self.make_resource('industry', Industry)
        topics = self.make_resource('topics', Topics)
        types = self.make_resource('types', Types)
        functions = self.make_resource('functions', Functions)
        world = self.make_resource('world', World)
        csv = Messages()
        #handler = Messages()
        #handler.load_state_from_string(MESSAGES_DATA)
        #rows = list(handler.get_rows())
        #print rows
        #load_state = handler.load_state_from_string
        #print load_state
        messages = self.make_resource('messages', CSV)
        # Add the core website uri - http://zmgc.net, http://lmz.fr ...
        # You can change this to suit your needs.
        hosts = ['zmgc.net', 'zmgc.aqoon.local']
        phoenix = self.make_resource('phoenix', Phoenix,
            title={'en': u'Zeitgeist Movement Global Connect'},
            website_is_open='community',
            website_languages=('en', 'fr'),
            vhosts=hosts,
            description={'en':u'One back-office to bring them all and in the'
                      u' darkness bind them, in an'
                      u' anarchically scalable information system.'},
            industry=('social',)
            )
        # We now create the core modules
        blog = phoenix.make_resource('blog', Blog, title={'en': u'ZMGC Blog'},)
        calendar = phoenix.make_resource('calendar', Calendar, title={'en': u'ZMGC Calendar'},)
        forums = phoenix.make_resource('forums', Forums, title={'en': u'ZMGC Forums'},)
        tracker = phoenix.make_resource('tracker', Tracker, title={'en': u'ZMGC Issue Tracker'},)
        wiki = phoenix.make_resource('wiki', WikiFolder, title={'en': u'ZMGC Wiki'})
        # We now add the chapters folder within which exists all other sites
        chapters = self.make_resource('chapters', Chapters,
                                        title={'en': u'Chapters'},
                                        description={'en': u'Chapters folder'})
        # We create the projects folder within which we store all the projects
        projects = self.make_resource('projects', Projects,
                                        title={'en': u'Projects'},
                                        description={'en': u'Projects folder'})
    
    ########################################################################
    # API
    ########################################################################
    # Restrict access to the folder's views
    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    last_changes = DBResource_CommitLog(access='is_allowed_to_edit')
    
    def get_version_of_packages(self, context):
        versions = BaseRoot.get_version_of_packages(self, context)
        # check nodejs version
        try:
            nodejs = get_pipe(['node', '--version'])
            versions['nodejs'] = nodejs
        except OSError:
            versions['nodejs'] = None

        return versions
    #######################################################################
    # Access control
    #######################################################################
    def is_allowed_to_create_chapter(self, user, resource):
        if user is None:
            return False
        if self.is_admin(user, resource):
            return True
        user_get_chapters = user.get_chapters()
        if user_get_chapters:
            context = get_context()
            context.message = MSG_EXISTING_CHAPTER_ADMIN
            return False
        return True
###########################################################################
# Register
###########################################################################
register_resource_class(Root)
