#!/usr/bin/env python
#
# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2016  Linutronix GmbH
#
# This file is part of ELBE.
#
# ELBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ELBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ELBE.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
from npyscreen import NPSAppManaged, FormMultiPage
from npyscreen import TitleText, TitleSelectOne, ButtonPress

from mako import exceptions
from mako.template import Template
from shutil import copyfile

from elbepack.directories import mako_template_dir

def template (deb, fname):
    return Template(filename=fname).render(**deb)

class Debianize (NPSAppManaged):
    def __init__ (self, debianizer):
        self.debianizer = debianizer
        NPSAppManaged.__init__ (self)

    def onStart (self):
        self.registerForm('MAIN', self.debianizer ())

class DebianizeForm (FormMultiPage):
    def __init__ (self):
        self.deb = { }
        self.tmpl_dir = None

        self.archs = ["armhf", "armel", "amd64", "i586", "powerpc"]
        self.formats = ["native", "git", "quilt"]
        self.releases = ["stable", "oldstable", "testing", "unstable", "experimental"]

        FormMultiPage.__init__ (self)

    def create (self):
        self.p_name = self.add_widget_intelligent (TitleText,
                name = "Name:", value = "elbe")

        self.p_version = self.add_widget_intelligent (TitleText,
                name = "Version:", value = "1.0")

        self.p_arch = self.add_widget_intelligent (TitleSelectOne,
                name = "Arch:",
                values = self.archs,
                value = [0],
                scroll_exit = True)

        self.source_format = self.add_widget_intelligent (TitleSelectOne,
                name="Format:",
                values = self.formats,
                value = [0],
                scroll_exit = True)

        self.release = self.add_widget_intelligent (TitleSelectOne,
                name = "Release:",
                values = self.releases,
                value = [0],
                scroll_exit = True)

        self.m_name = self.add_widget_intelligent (TitleText,
                name = "Maintainer:", value = "Max Mustermann")

        self.m_mail = self.add_widget_intelligent (TitleText,
                name = "Mail:", value = "max@mustermann.org")

        self.add_page ()
        self.gui ()

        self.add_widget_intelligent (ButtonPress, name = "Save",
                when_pressed_function=self.on_ok)

        self.add_widget_intelligent (ButtonPress, name = "Cancel",
                when_pressed_function=self.on_cancel)

    def on_ok (self):
        self.deb['k_name']       = self.p_name.get_value ()
        self.deb['k_debversion'] = self.p_version.get_value ()
        self.deb['k_debarch']    = self.archs [self.p_arch.get_value ()[0]]
        self.deb['m_name']       = self.m_name.get_value ()
        self.deb['m_mail']       = self.m_mail.get_value ()
        self.deb['source_format']= self.formats [self.source_format.get_value ()[0]]
        self.deb['release']       = self.releases [self.release.get_value ()[0]]

        os.mkdir ('debian')
        os.mkdir ('debian/source')

        self.debianize ()

        with open ('debian/source/format', 'w') as f:
            mako = os.path.join(self.tmpl_dir, 'format.mako')
            f.write (template(self.deb, mako))

        copyfile (os.path.join(self.tmpl_dir, 'copyright'), 'debian/copyright')
        with open ('debian/compat', 'w') as f:
            f.write ('9')

        sys.exit (0)

    def on_cancel (self):
        sys.exit (-2)


class Autotools (DebianizeForm):
    def __init__ (self):
        print ('autotools not supported at the moment')
        sys.exit (-2)
        DebianizeForm.__init__ (self)

class Kernel (DebianizeForm):
    def __init__ (self):
        self.imgtypes = ["zImage", "uImage", "Image"]
        DebianizeForm.__init__ (self)

    def gui (self):
        self.loadaddr = self.add_widget_intelligent (TitleText,
                name="Loadaddress:", value="0x800800")

        self.defconfig = self.add_widget_intelligent (TitleText,
                name="defconfig:", value="omap2plus_defconfig")

        self.imgtype = self.add_widget_intelligent (TitleSelectOne,
                name="Image Format:", values = self.imgtypes,
                value = [0],
                scroll_exit=True)

        self.cross = self.add_widget_intelligent (TitleText,
                name="CROSS_COMPILE", value="arm-linux-gnueabihf-")

        self.k_version = self.add_widget_intelligent (TitleText,
                name="Kernelversion", value="4.4")

    def debianize (self):
        if self.deb['k_debarch'] == 'armhf':
            self.deb['k_arch'] = 'arm'
        elif self.deb['k_debarch'] == 'armel':
            self.deb['k_arch'] = 'arm'
        else:
            self.deb['k_arch'] = self.deb['k_debarch']

        self.deb['loadaddr']      = self.loadaddr.get_value ()
        self.deb['defconfig']     = self.defconfig.get_value ()
        self.deb['imgtype']       = self.imgtypes [self.imgtype.get_value ()[0]]
        self.deb['cross_compile'] = self.cross.get_value ()
        self.deb['k_version']     = self.k_version.get_value ()

        self.tmpl_dir = os.path.join(mako_template_dir, 'debianize/kernel')
        pkg_name = self.deb['k_name']+'-'+self.deb['k_version']

        for tmpl in ['control', 'rules']:
            with open (os.path.join('debian/', tmpl), 'w') as f:
                mako = os.path.join(self.tmpl_dir, tmpl+'.mako')
                f.write (template(self.deb, mako))

        cmd = 'dch --package linux-' + pkg_name + \
                   ' -v ' + self.deb['k_debversion'] + \
                   ' --create -M -D ' + self.deb['release'] + \
                   ' "generated by elbe debianize"'
        os.system (cmd)

        copyfile (os.path.join(self.tmpl_dir, 'linux-image.install'),
                  'debian/linux-image-'+pkg_name+'.install')
        copyfile (os.path.join(self.tmpl_dir, 'linux-headers.install'),
                  'debian/linux-headers-'+pkg_name+'.install')

#TODO before adding another helper, refactor the code to be 'plugin-like',
# see finetuning for example.
debianizer = {'kernel':    Kernel,
              'autotools': Autotools}

files = {'kernel': ['Kbuild', 'Kconfig', 'MAINTAINERS', 'REPORTING-BUGS'],
         'autotools': ['configure.ac'] }

def run_command ( args ):
    if os.path.exists ('debian'):
        print 'debian folder already exists, nothing to do'
        sys.exit (-1)

    for key in files.keys ():
       match = True
       for f in files[key]:
           if not os.path.exists (f):
               match = False
       if match:
           Debianize (debianizer[key]).run ()
           sys.exit(-1)

    print ("this creates a debinization of a kernel source")
    print ("please run the command from kernel source dir")
    sys.exit (-2)
