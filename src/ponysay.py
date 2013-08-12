#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
ponysay - Ponysay, cowsay reimplementation for ponies

Copyright (C) 2012, 2013  Erkin Batu Altunbaş et al.


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


If you intend to redistribute ponysay or a fork of it commercially,
it contains aggregated images, some of which may not be commercially
redistribute, you would be required to remove those. To determine
whether or not you may commercially redistribute an image make use
that line ‘FREE: yes’, is included inside the image between two ‘$$$’
lines and the ‘FREE’ is and upper case and directly followed by
the colon.
'''
from common import *
from backend import *
from balloon import *
from spellocorrecter import *
from ucs import *
from kms import *
from list import *
from metadata import *



class Ponysay():
    '''
    This is the mane class of ponysay
    '''
    
    def __init__(self):
        '''
        Constructor
        '''
        
        # The user's home directory
        self.HOME = os.environ['HOME'] if 'HOME' in os.environ else ''
        if len(self.HOME) == 0:
            os.environ['HOME'] = self.HOME = os.path.expanduser('~')
        
        
        ## Change system enviroment variables with ponysayrc
        for file in ('$XDG_CONFIG_HOME/ponysay/ponysayrc', '$HOME/.config/ponysay/ponysayrc', '$HOME/.ponysayrc', '/etc/ponysayrc'):
            file = Ponysay.__parseFile(file)
            if (file is not None) and os.path.exists(file):
                with open(file, 'rb') as ponysayrc:
                    code = ponysayrc.read().decode('utf8', 'replace') + '\n'
                    env = os.environ
                    code = compile(code, file, 'exec')
                    exec(code)
                break
        
        self.HOME = os.environ['HOME'] if 'HOME' in os.environ else '' # in case ~/.ponysayrc changes it
        if len(self.HOME) == 0:
            os.environ['HOME'] = self.HOME = os.path.expanduser('~')
        
        
        # Whether any unrecognised options was parsed, this should be set by the invoker before run()
        self.unrecognised = False
        
        
        # Whether the program is execute in Linux VT (TTY)
        self.linuxvt = ('TERM' in os.environ) and (os.environ['TERM'] == 'linux')
        
        # Whether the script is executed as ponythink
        self.isthink = Ponysay.__isPonythink()
        
        
        # Whether stdin is piped
        self.pipelinein = not sys.stdin.isatty()
        
        # Whether stdout is piped
        self.pipelineout = not sys.stdout.isatty()
        
        # Whether stderr is piped
        self.pipelineerr = not sys.stderr.isatty()
        
        
        # Whether KMS is used
        self.usekms = KMS.usingKMS(self.linuxvt)
        
        
        # Mode string that modifies or adds $ variables in the pony image
        self.mode = ''
        
        
        # The directories where pony files are stored, ttyponies/ are used if the terminal is Linux VT (also known as TTY) and not with KMS
        self.xponydirs = Ponysay.__getShareDirectories('ponies/'):
        self.vtponydirs = Ponysay.__getShareDirectories('ttyponies/'):
        
        # The directories where pony files are stored, extrattyponies/ are used if the terminal is Linux VT (also known as TTY) and not with KMS
        self.extraxponydirs = Ponysay.__getShareDirectories('extraponies/'):
        self.extravtponydirs = Ponysay.__getShareDirectories('extrattyponies/'):
        
        # The directories where quotes files are stored
        self.quotedirs = Ponysay.__getShareDirectories('quotes/'):
        
        # The directories where balloon style files are stored
        self.balloondirs = Ponysay.__getShareDirectories('balloons/'):
        
        # ucsmap files
        self.ucsmaps = Ponysay.__getShareDirectories('ucsmap/'):
        
        
    def __parseFile(file):
        '''
        Parse a file name encoded with environment variables
        
        @param   file  The encoded file name
        @return        The target file name, None if the environment variables are not declared
        '''
        if '$' in file:
            buf = ''
            esc = False
            var = None
            for c in file:
                if esc:
                    buf += c
                    esc = False
                elif var is not None:
                    if c == '/':
                        var = os.environ[var] if var in os.environ else ''
                        if len(var) == 0:
                            return None
                        buf += var + c
                        var = None
                    else:
                        var += c
                elif c == '$':
                    var = ''
                elif c == '\\':
                    esc = True
                else:
                    buf += c
            return buf
        return file

    
    def __getShareDirectories(directory):
        '''
        Gets existing unique /share directories
        
        @param   directory:str  The directory base name
        @return  :list<str>     Absolute directory names
        '''
        appendset = set()
        rc = []
        _ponydirs = Ponysay.__share(directory)
        for ponydir in _ponydirs:
            if (ponydir is not None) and os.path.isdir(ponydir) and (ponydir not in appendset):
                rc.append(ponydir)
                appendset.add(ponydir)
        return rc
    
    
    def __share(file):
        '''
        Gets /share files
        
        @param   file:str    The file base name
        @return  :list<str>  Absolute file names
        '''
        def cat(a, b):
            if a is None:
                return None
            return a + b
        return [cat(Ponysay.__parseFile(item), file) for item in [
                './',
                '$XDG_DATA_HOME/ponysay/',
                '$HOME/.local/share/ponysay/',
                '/usr/share/ponysay/'
               ]]
    
    
    def __isPonythink():
        '''
        Check if ponythink is executed
        '''
        isthink = sys.argv[0]
        if os.sep in isthink:
            isthink = isthink[isthink.rfind(os.sep) + 1:]
        if os.extsep in isthink:
            isthink = isthink[:isthink.find(os.extsep)]
        isthink = isthink.endswith('think')
        return isthink
    
    
    
    def run(self, args):
        '''
        Starts the part of the program the arguments indicate
        
        @param  args:ArgParser  Parsed command line arguments
        '''
        if (args.argcount == 0) and not self.pipelinein:
            args.help()
            exit(254)
            return
        
        def test(*keys):
            '''
            Test arguments written in negation-free disjunctive normal form
            
            @param   keys:*str|itr<str>  A list of keys and set of keys, any of which must exists, a set of keys only passes if all of those exists
            @return  :bool               Whether the check passed
            '''
            for key in keys:
                if isinstance(key, str):
                    if args.opts[key] is not None:
                        return True
                else:
                    for skey in key:
                        if args.opts[skey] is None:
                            return False
                    return True
            return False
        
        ## Emulate termial capabilities
        if   test('-X'):  (self.linuxvt, self.usekms) = (False, False)
        elif test('-V'):  (self.linuxvt, self.usekms) = (True, False)
        elif test('-K'):  (self.linuxvt, self.usekms) = (True, True)
        self.ponydirs      = self.vtponydirs      if self.linuxvt and not self.usekms else self.xponydirs
        self.extraponydirs = self.extravtponydirs if self.linuxvt and not self.usekms else self.extraxponydirs
        
        ## Variadic variants of -f, -q &c
        for sign in ('-', '+'):
            for letter in ('f', 'F', 'q', 'Q'):
                ssl = sign + sign + letter
                sl = sign + letter
                if (ssl in args.opts) and (args.opts[ssl] is not None):
                    if args.opts[sl] is not None:  args.opts[sl] += args.opts[ssl]
                    else:                          args.opts[sl]  = args.opts[ssl]
        
        ## Save whether standard or extra ponies are used
        self.usingstandard = test('-f', '-F', '-q') # -Q
        self.usingextra    = test('+f', '-F') # +q -Q
        
        ## Run modes
        if   test('-h'):                                     args.help()
        elif test('-v'):                                     self.version()
        elif test('--quoters'):                              self.quoters(True, False)
        elif test('--Onelist', ('--onelist', '++onelist')):  self.onelist(True, True)
        elif test('--onelist'):                              self.onelist(True, False)
        elif test('++onelist'):                              self.onelist(False, True)
        elif test('+A', ('-L', '+L')):                       self.linklist(); self.__extraponies(); self.linklist()
        elif test('-A', ('-l', '+l')):                       self.list(); self.__extraponies(); self.list()
        elif test('-L'):                                     self.linklist()
        elif test('-l'):                                     self.list()
        elif test('+L'):                                     self.__extraponies(); self.linklist()
        elif test('+l'):                                     self.__extraponies(); self.list()
        elif test('-B'):                                     self.balloonlist()
        else:
            ## Colouring features
            if test('--colour-pony'):
                self.mode += '\033[' + ';'.join(args.opts['--colour-pony']) + 'm'
            else:
                self.mode += '\033[0m'
            if test('+c'):
                if args.opts['--colour-msg']    is None:  args.opts['--colour-msg']    = args.opts['+c']
                if args.opts['--colour-link']   is None:  args.opts['--colour-link']   = args.opts['+c']
                if args.opts['--colour-bubble'] is None:  args.opts['--colour-bubble'] = args.opts['+c']
            
            ## Other extra features
            self.__bestpony(args)
            self.__ucsremap(args)
            if test('-o'):
                self.mode += '$/= $$\\= $'
                args.message = ''
                self.ponyonly = True
            else:
                self.ponyonly = False
            if test('-i', '+i'):
                args.message = ''
            self.restriction = args.opts['-r']
            
            ## The stuff
            if not self.unrecognised:
                self.printPony(args)
            else:
                args.help()
                exit(255)
                return
    
    
    
    ##############################################
    ## Methods that run before the mane methods ##
    ##############################################
    
    def __extraponies(self):
        '''
        Use extra ponies
        '''
        ## Change ponydir to extraponydir
        self.ponydirs[:] = self.extraponydirs
        self.quotedirs[:] = [] ## TODO +q
    
    
    def __bestpony(self, args):
        '''
        Use best.pony if nothing else is set
        
        @param  args:ArgParser     Parsed command line arguments
        '''
        ## Set best.pony as the pony to display if none is selected
        def test(keys, strict):
            if strict:
                for key in keys:
                    if (args.opts[key] is not None) and (len(args.opts[key]) != 0):
                        return False
            else:
                for key in keys:
                    if args.opts[key] is not None:
                        return False
            return True
        keys = ['-f', '+f', '-F', '-q'] ## TODO +q -Q
        if test(keys, False):
            for ponydir in self.ponydirs:
                if os.path.isfile(ponydir + 'best.pony') or os.path.islink(ponydir + 'best.pony'):
                    pony = os.path.realpath(ponydir + 'best.pony') # Canonical path
                    if test(keys, True):
                        args.opts['-f'] = [pony]
                    else:
                        for key in keys:
                            if test(key, True):
                                args.opts[key] = [pony]
                    break
    
    
    def __ucsremap(self, args):
        '''
        Apply pony name remapping to args according to UCS settings
        
        @param  args:ArgParser  Parsed command line arguments
        '''
        ## Read UCS configurations
        env_ucs = os.environ['PONYSAY_UCS_ME'] if 'PONYSAY_UCS_ME' in os.environ else ''
        ucs_conf = 0
        if   env_ucs in ('yes',    'y', '1'):  ucs_conf = 1
        elif env_ucs in ('harder', 'h', '2'):  ucs_conf = 2
        
        ## Stop UCS is not used
        if ucs_conf == 0:
            return
        
        ## Read all lines in all UCS → ASCII map files
        maplines = []
        for ucsmap in self.ucsmaps:
            if os.path.isfile(ucsmap):
                with open(ucsmap, 'rb') as mapfile:
                    maplines += [line.replace('\n', '') for line in mapfile.read().decode('utf8', 'replace').split('\n')]
        
        ## Create UCS → ASCII mapping from read lines
        map = {}
        stripset = ' \t' # must be string, wtf! and way doesn't python's doc say so
        for line in maplines:
            if (len(line) > 0) and not (line[0] == '#'):
                s = line.index('→')
                ucs   = line[:s]    .strip(stripset)
                ascii = line[s + 1:].strip(stripset)
                map[ucs] = ascii
        
        ## Apply UCS → ASCII mapping to -f, +f, -F and -q arguments
        for flag in ('-f', '+f', '-F', '-q'): ## TODO +q -Q
            if args.opts[flag] is not None:
                for i in range(0, len(args.opts[flag])):
                    if args.opts[flag][i] in map:
                        args.opts[flag][i] = map[args.opts[flag][i]]
    
    
    #######################
    ## Auxiliary methods ##
    #######################
    
    def __ucsise(self, ponies, links = None):
        '''
        Apply UCS:ise pony names according to UCS settings
        
        @param  ponies:list<str>      List of all ponies (of interrest)
        @param  links:map<str, str>?  Map to fill with simulated symlink ponies, may be `None`
        '''
        ## Read UCS configurations
        env_ucs = os.environ['PONYSAY_UCS_ME'] if 'PONYSAY_UCS_ME' in os.environ else ''
        ucs_conf = 0
        if   env_ucs in ('yes',    'y', '1'):  ucs_conf = 1
        elif env_ucs in ('harder', 'h', '2'):  ucs_conf = 2
        
        ## Stop UCS is not used
        if ucs_conf == 0:
            return
        
        ## Read all lines in all UCS → ASCII map files
        maplines = []
        for ucsmap in self.ucsmaps:
            if os.path.isfile(ucsmap):
                with open(ucsmap, 'rb') as mapfile:
                    maplines += [line.replace('\n', '') for line in mapfile.read().decode('utf8', 'replace').split('\n')]
        
        ## Create UCS → ASCII mapping from read lines
        map = {}
        stripset = ' \t' # must be string, wtf! and way doesn't python's doc say so
        for line in maplines:
            if not line.startswith('#'):
                s = line.index('→')
                ucs   = line[:s]    .strip(stripset)
                ascii = line[s + 1:].strip(stripset)
                map[ascii] = ucs
        
        ## Apply UCS → ASCII mapping to ponies, by alias if weak settings
        if ucs_conf == 1:
            for pony in ponies:
                if pony in map:
                    ponies.append(map[pony])
                    if links is not None:
                        links[map[pony]] = pony
        else:
            for j in range(0, len(ponies)):
                if ponies[j] in map:
                    ponies[j] = map[ponies[j]]
    
    
    def __getpony(self, selection, args, alt = False):
        '''
        Returns one file with full path and ponyquote that should be used, names is filter for names, also accepts filepaths
        
        @param   selection:(name:str, dirs:itr<str>, quote:bool)?  Parsed command line arguments as name–directories–quoting tubles:
                                                                       name:      The pony name
                                                                       dirfiles:  Files, with the directory, in the pony directories
                                                                       quote:     Whether to use ponyquotes
        @param   args:ArgParser                                    Parsed command line arguments
        @param   alt:bool                                          For method internal use...
        @return  (path, quote):(str, str?)                         The file name of a pony, and the ponyquote that should be used if any
        '''
        ## If there is no selected ponies, choose all of them
        if (selection is None) or (len(selection) == 0):
            quote    =  args.opts['-q'] is not None ## TODO +q -Q
            standard = (args.opts['-f'] is not None) or (args.opts['-F'] is not None) or (args.opts['-q'] is not None) ## TODO -Q
            extra    = (args.opts['+f'] is not None) or (args.opts['-F'] is not None) ## TODO +q -Q
            if not (standard or extra):
                standard = True
            ponydirs = (self.ponydirs if standard else []) + (self.extraponydirs if extra else []);
            quoters  = self.__quoters() if standard and quote else None ## TODO +q -Q
            if (quoters is not None) and (len(quoters) == 0):
                printerr('Princess Celestia! All the ponies are mute!')
                exit(250)
            
            ## Get all ponies, with quotes
            oldponies = {}
            if standard:
                for ponydir in self.ponydirs:
                    for ponyfile in os.listdir(ponydir):
                        if endswith(ponyfile, '.pony'):
                            pony = ponyfile[:-5]
                            if (pony not in oldponies) and ((quoters is None) or (pony in quoters)):
                                oldponies[pony] = ponydir + ponyfile
            if extra:
                for ponydir in self.extraponydirs:
                    for ponyfile in os.listdir(ponydir):
                        if endswith(ponyfile, '.pony'):
                            pony = ponyfile[:-5]
                            if pony not in oldponies:
                                oldponies[pony] = ponydir + ponyfile
            
            ## Apply metadata restriction
            if self.restriction is not None:
                logic = Metadata.makeRestrictionLogic(self.restriction)
                ponies = {}
                for ponydir in ponydirs:
                    for pony in Metadata.restrictedPonies(ponydir, logic):
                        if (pony in oldponies) and not (pony in ponies):
                            ponies[pony] = ponydir + pony + '.pony'
                if len(ponies) > 0:
                    oldponies = ponies
            
            ## Apply dimension restriction
            ponies = {}
            (termh, termw) = gettermsize()
            for ponydir in ponydirs:
                (fitw, fith) = (None, None)
                if os.path.exists(ponydir + 'widths'):
                    fitw = set()
                    with open(ponydir + 'widths', 'rb') as file:
                        Metadata.getFitting(fitw, termw, file)
                if os.path.exists(ponydir + ('onlyheights' if self.ponyonly else 'heights')):
                    fith = set()
                    with open(ponydir + ('onlyheights' if self.ponyonly else 'heights'), 'rb') as file:
                        Metadata.getFitting(fith, termh, file)
                for ponyfile in oldponies.values():
                    if ponyfile.startswith(ponydir):
                        pony = ponyfile[len(ponydir) : -5]
                        if (fitw is None) or (pony in fitw):
                            if (fith is None) or (pony in fith):
                                ponies[pony] = ponyfile
            
            ## Select one pony and set all information
            names = list((oldponies if len(ponies) == 0 else ponies).keys())
            if len(names) == 0:
                printerr('All the ponies are missing, call the Princess!')
                exit(249)
            pony = names[random.randrange(0, len(names))]
            selection = [(pony, [ponies[pony]], quote)]
        
        ## Select a random pony of the choosen ones
        pony = selection[random.randrange(0, len(selection))]
        if os.path.exists(pony[0]):
            ponyname = pony[0].split(os.sep)[-1]
            if os.extsep in ponyname:
                ponyname = ponyname[:ponyname.rfind(os.extsep)]
            return (pony[0], self.__getquote(ponyname, pony[0]) if pony[2] else None)
        else:
            possibilities = [f.split(os.sep)[-1][:-5] for f in pony[1]]
            if pony[0] not in possibilities:
                if not alt:
                    autocorrect = SpelloCorrecter(possibilities)
                    (alternatives, dist) = autocorrect.correct(pony[0])
                    limit = os.environ['PONYSAY_TYPO_LIMIT'] if 'PONYSAY_TYPO_LIMIT' in os.environ else ''
                    limit = 5 if len(limit) == 0 else int(limit)
                    if (len(alternatives) > 0) and (dist <= limit):
                        (_, files, quote) = pony
                        return self.__getpony([(a, files, quote) for a in alternatives], True)
                printerr('I have never heard of anypony named %s' % pony[0]);
                if not self.usingstandard:
                    printerr('Use -f/-q or -F if it a MLP:FiM pony');
                if not self.usingextra:
                    printerr('Have you tested +f or -F?');
                exit(252)
            else:
                file = pony[1][possibilities.index(pony[0])]
                return (file, self.__getquote(pony[0], file) if pony[2] else None)
    
    
    def __getquote(self, pony, file):
        '''
        Select a quote for a pony
        
        @param   pony:str  The pony name
        @param   file:str  The pony's file name
        @return  :str      A quote from the pony, with a failure fall back message
        '''
        quote = []
        if (os.path.dirname(file) + os.sep).replace(os.sep + os.sep, os.sep) in self.ponydirs:
            realpony = pony
            if os.path.islink(file):
                realpony = os.path.basename(os.path.realpath(file))
                if os.extsep in realpony:
                    realpony = realpony[:realpony.rfind(os.extsep)]
            quote = self.__quotes(ponies = [realpony])
        if len(quote) == 0:
            quote = 'Zecora! Help me, I am mute!'
        else:
            quote = quote[random.randrange(0, len(quote))][1]
            printinfo('quote file: ' + quote)
            with open(quote, 'rb') as qfile:
                quote = qfile.read().decode('utf8', 'replace').strip()
        return quote
    
    
    def __quoters(self, ponydirs = None, quotedirs = None):
        '''
        Returns a set with all ponies that have quotes and are displayable
        
        @param   ponydirs:itr<str>?   The pony directories to use
        @param   quotedirs:itr<str>?  The quote directories to use
        @return  :set<str>            All ponies that have quotes and are displayable
        '''
        if ponydirs  is None:  ponydirs  = self.ponydirs
        if quotedirs is None:  quotedirs = self.quotedirs
        
        ## List all unique quote files
        quotes = []
        quoteshash = set()
        _quotes = []
        for quotedir in quotedirs:
            _quotes += [item[:item.index('.')] for item in os.listdir(quotedir)]
        for quote in _quotes:
            if not quote == '':
                if not quote in quoteshash:
                    quoteshash.add(quote)
                    quotes.append(quote)
        
        ## Create a set of all ponyes that have quotes
        ponies = set()
        for ponydir in ponydirs:
            for pony in os.listdir(ponydir):
                if not pony[0] == '.':
                    p = pony[:-5] # remove .pony
                    for quote in quotes:
                        if ('+' + p + '+') in ('+' + quote + '+'):
                            if not p in ponies:
                                ponies.add(p)
        
        return ponies
    
    
    def __quotes(self, ponydirs = None, quotedirs = None, ponies = None):
        '''
        Returns a list with all (pony, quote file) pairs
        
        @param   ponydirs:itr<str>?        The pony directories to use
        @param   quotedirs:itr<str>?       The quote directories to use
        @param   ponies:itr<str>?          The ponies to use
        @return  (pony, quote):(str, str)  All ponies–quote file-pairs
        '''
        if ponydirs  is None:  ponydirs  = self.ponydirs
        if quotedirs is None:  quotedirs = self.quotedirs
        
        ## Get all ponyquote files
        quotes = []
        for quotedir in quotedirs:
            quotes += [quotedir + item for item in os.listdir(quotedir)]
        
        ## Create list of all pony–quote file-pairs
        rc = []
        if ponies is None:
            for ponydir in ponydirs:
                for pony in os.listdir(ponydir):
                    if endswith(pony, '.pony'):
                        p = pony[:-5] # remove .pony
                        for quote in quotes:
                            q = quote[quote.rindex('/') + 1:]
                            q = q[:q.rindex('.')]
                            if ('+' + p + '+') in ('+' + q + '+'):
                                rc.append((p, quote))
        else:
            for p in ponies:
                for quote in quotes:
                    q = quote[quote.rindex('/') + 1:]
                    q = q[:q.rindex('.')]
                    if ('+' + p + '+') in ('+' + q + '+'):
                        rc.append((p, quote))
        
        return rc
    
    
    
    #####################
    ## Listing methods ##
    #####################
    
    def list(self, ponydirs = None):
        '''
        Lists the available ponies
        
        @param  ponydirs:itr<str>?  The pony directories to use
        '''
        List.simplelist(self.ponydirs if ponydirs is None else ponydirs,
                        self.__quoters(), lambda x : self.__ucsise(x))
    
    
    def linklist(self, ponydirs = None):
        '''
        Lists the available ponies with alternatives inside brackets
        
        @param  ponydirs:itr<str>  The pony directories to use
        '''
        List.linklist(self.ponydirs if ponydirs is None else ponydirs,
                      self.__quoters(), lambda x, y : self.__ucsise(x, y))
    
    
    def onelist(self, standard = True, extra = False):
        '''
        Lists the available ponies on one column without anything bold or otherwise formated
        
        @param  standard:bool  Include standard ponies
        @param  extra:bool     Include extra ponies
        '''
        List.onelist(self.ponydirs if standard else None,
                     self.extraponydirs if extra else None,
                     lambda x : self.__ucsise(x))
    
    
    def quoters(self, standard = True, extra = False):
        '''
        Lists with all ponies that have quotes and are displayable, on one column without anything bold or otherwise formated
        
        @param  standard:bool  Include standard ponies
        @param  extra:bool     Include extra ponies
        '''
        ## Get all quoters
        ponies = list(self.__quoters()) if standard else []
        
        ## And now the extra ponies
        if extra:
            self.__extraponies()
            ponies += list(self.__quoters())
        
        ## UCS:ise here
        self.__ucsise(ponies)
        ponies.sort()
        
        ## Print each one on a seperate line, but skip duplicates
        last = ''
        for pony in ponies:
            if not pony == last:
                last = pony
                print(pony)
    
    
    
    #####################
    ## Balloon methods ##
    #####################
    
    def balloonlist(self):
        '''
        Prints a list of all balloons
        '''
        List.balloonlist(self.balloondirs, self.isthink)
    
    
    def __getballoonpath(self, names, alt = False):
        '''
        Returns one file with full path, names is filter for style names, also accepts filepaths
        
        @param  names:list<str>  Balloons to choose from, may be `None`
        @param  alt:bool         For method internal use
        @param  :str             The file name of the balloon, will be `None` iff `names` is `None`
        '''
        ## Stop if their is no choosen balloon
        if names is None:
            return None
        
        ## Get all balloons
        balloons = {}
        for balloondir in self.balloondirs:
            for balloon in os.listdir(balloondir):
                balloonfile = balloon
                ## Use .think if running ponythink, otherwise .say
                if self.isthink and endswith(balloon, '.think'):
                    balloon = balloon[:-6]
                elif (not self.isthink) and endswith(balloon, '.say'):
                    balloon = balloon[:-4]
                else:
                    continue
                
                ## Add the balloon if there is none with the same name
                if balloon not in balloons:
                    balloons[balloon] = balloondir + balloonfile
        
        ## Support for explicit balloon file names
        for name in names:
            if os.path.exists(name):
                balloons[name] = name
        
        ## Select a random balloon of the choosen ones
        balloon = names[random.randrange(0, len(names))]
        if balloon not in balloons:
            if not alt:
                autocorrect = SpelloCorrecter(self.balloondirs, '.think' if self.isthink else '.say')
                (alternatives, dist) = autocorrect.correct(balloon)
                limit = os.environ['PONYSAY_TYPO_LIMIT'] if 'PONYSAY_TYPO_LIMIT' in os.environ else ''
                limit = 5 if len(limit) == 0 else int(limit)
                if (len(alternatives) > 0) and (dist <= limit):
                    return self.__getballoonpath(alternatives, True)
            printerr('That balloon style %s does not exist' % balloon)
            exit(251)
        else:
            return balloons[balloon]
    
    
    def __getballoon(self, balloonfile):
        '''
        Creates the balloon style object
        
        @param   balloonfile:str  The file with the balloon style, may be `None`
        @return  :Balloon         Instance describing the balloon's style
        '''
        return Balloon.fromFile(balloonfile, self.isthink)
    
    
    
    ########################
    ## Displaying methods ##
    ########################
    
    def version(self):
        '''
        Prints the name of the program and the version of the program
        '''
        ## Prints the "ponysay $VERSION", if this is modified, ./dev/dist.sh must be modified accordingly
        print('%s %s' % ('ponysay', VERSION))
    
    
    def printPony(self, args):
        '''
        Print the pony with a speech or though bubble. message, pony and wrap from args are used.
        
        @param  args:ArgParser  Parsed command line arguments
        '''
        ## Get the pony
        (selection, standard, extra) = ([], [], [])
        for ponydir in self.ponydirs:
            for pony in os.listdir(ponydir):
                if endswith(pony, '.pony'):
                    standard.append(ponydir + pony)
        for ponydir in self.extraponydirs:
            for pony in os.listdir(ponydir):
                if endswith(pony, '.pony'):
                    extra.append(ponydir + pony)
        both = standard + extra
        if args.opts['-f'] is not None:
            for pony in args.opts['-f']:  selection.append((pony, standard, False))
        if args.opts['+f'] is not None:
            for pony in args.opts['+f']:  selection.append((pony, extra, False))
        if args.opts['-F'] is not None:
            for pony in args.opts['-F']:  selection.append((pony, both, False))
        if args.opts['-q'] is not None:
            for pony in args.opts['-q']:  selection.append((pony, standard, True))
        ## TODO +q -Q
        (pony, quote) = self.__getpony(selection, args)
        
        ## Get message and remove tailing whitespace from stdin (but not for each line)
        msg = None
        if quote is not None:
            msg = quote
        elif args.message is None:
            msg = ''.join(sys.stdin.readlines()).rstrip()
        else:
            msg = args.message
        if args.opts['--colour-msg'] is not None:
            msg = '\033[' + ';'.join(args.opts['--colour-msg']) + 'm' + msg
        
        ## This algorithm should give some result as cowsay's (according to tests)
        if args.opts['-c'] is not None:
            buf = ''
            last = ' '
            CHARS = '\t \n'
            for c in msg:
                if (c in CHARS) and (last in CHARS):
                    if last == '\n':
                        buf += last
                    last = c
                else:
                    buf += c
                    last = c
            msg = buf.strip(CHARS)
            buf = ''
            for c in msg:
                if (c != '\n') or (last != '\n'):
                    buf += c
                    last = c
            msg = buf.replace('\n', '\n\n')
        
        ## Print info
        printinfo('pony file: ' + pony)
        
        ## Use PNG file as pony file
        if endswith(pony.lower(), '.png'):
            pony = '\'' + pony.replace('\'', '\'\\\'\'') + '\''
            pngcmd = 'ponytool --import image --file %s --balloon n --export ponysay --platform %s --balloon y'
            pngcmd %= (pony, ('linux' if self.linuxvt else 'xterm')) # XXX xterm should be haiku in Haiku
            pngpipe = os.pipe()
            Popen(pngcmd, stdout=os.fdopen(pngpipe[1], 'w'), shell=True).wait()
            pony = '/proc/' + str(os.getpid()) + '/fd/' + str(pngpipe[0])
        
        ## If KMS is utilies, select a KMS pony file and create it if necessary
        pony = KMS.kms(pony, self.HOME, self.linuxvt)
        
        ## If in Linux VT clean the terminal (See info/pdf-manual [Printing in TTY with KMS])
        if self.linuxvt:
            print('\033[H\033[2J', end='')
        
        ## Get width truncation and wrapping
        env_width = os.environ['PONYSAY_FULL_WIDTH'] if 'PONYSAY_FULL_WIDTH' in os.environ else None
        if env_width is None:  env_width = ''
        widthtruncation = gettermsize()[1] if env_width not in ('yes', 'y', '1') else None
        messagewrap = 60
        if (args.opts['-W'] is not None) and (len(args.opts['-W'][0]) > 0):
            messagewrap = args.opts['-W'][0]
            if messagewrap[0] in 'nmsNMS': # m is left to n on QWERTY and s is left to n on Dvorak
                messagewrap = None
            elif messagewrap[0] in 'iouIOU': # o is left to i on QWERTY and u is right to i on Dvorak
                messagewrap = gettermsize()[1]
            else:
                messagewrap = int(args.opts['-W'][0])
        
        ## Get balloon object
        balloonfile = self.__getballoonpath(args.opts['-b'] if args.opts['-b'] is not None else None)
        printinfo('balloon style file: ' + str(balloonfile))
        balloon = self.__getballoon(balloonfile) if args.opts['-o'] is None else None
        
        ## Get hyphen style
        hyphen = os.environ['PONYSAY_WRAP_HYPHEN'] if 'PONYSAY_WRAP_HYPHEN' in os.environ else None
        if (hyphen is None) or (len(hyphen) == 0):
            hyphen = '-'
        hyphencolour = ''
        if args.opts['--colour-wrap'] is not None:
            hyphencolour = '\033[' + ';'.join(args.opts['--colour-wrap']) + 'm'
        hyphen = '\033[31m' + hyphencolour + hyphen
        
        ## Link and balloon colouring
        linkcolour = ''
        if args.opts['--colour-link'] is not None:
            linkcolour = '\033[' + ';'.join(args.opts['--colour-link']) + 'm'
        ballooncolour = ''
        if args.opts['--colour-bubble'] is not None:
            ballooncolour = '\033[' + ';'.join(args.opts['--colour-bubble']) + 'm'
        
        ## Determine --info/++info settings
        minusinfo = args.opts['-i'] is not None
        plusinfo  = args.opts['+i'] is not None
        
        ## Run cowsay replacement
        backend = Backend(message = msg, ponyfile = pony, wrapcolumn = messagewrap, width = widthtruncation, balloon = balloon,
                          hyphen = hyphen, linkcolour = linkcolour, ballooncolour = ballooncolour, mode = self.mode,
                          infolevel = 2 if plusinfo else (1 if minusinfo else 0))
        backend.parse()
        output = backend.output
        if output.endswith('\n'):
            output = output[:-1]
        
        
        ## Load height trunction settings
        env_bottom = os.environ['PONYSAY_BOTTOM'] if 'PONYSAY_BOTTOM' in os.environ else None
        if env_bottom is None:  env_bottom = ''
        
        env_height = os.environ['PONYSAY_TRUNCATE_HEIGHT'] if 'PONYSAY_TRUNCATE_HEIGHT' in os.environ else None
        if env_height is None:  env_height = ''
        
        env_lines = os.environ['PONYSAY_SHELL_LINES'] if 'PONYSAY_SHELL_LINES' in os.environ else None
        if (env_lines is None) or (env_lines == ''):  env_lines = '2'
        
        ## Print the output, truncated on height is so set
        lines = gettermsize()[0] - int(env_lines)
        if self.linuxvt or (env_height is ('yes', 'y', '1')):
            if env_bottom is ('yes', 'y', '1'):
                for line in output.split('\n')[: -lines]:
                    print(line)
            else:
                for line in output.split('\n')[: lines]:
                    print(line)
        else:
            print(output)

