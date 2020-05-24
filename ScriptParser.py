import re

from Reply import Reply
from Character import Character
from Movie import Movie

class ScriptParser():
	"""Parser for movie scripts. """

	minimum_replies = 1 # number of replies under which a character will not be kept in the results
	minimum_characters = 5 # number of characters required to consider a script parsed

	character_blacklist = [
		' - ', ' -- ', '...', 
		'LATER', 'LATE', 'FADE OUT', 'FADE IN', 'CUT TO', 'EXT.', 'EXTERIOR',
		'INT.', 'INTERIOR', 'INSIDE', 'OUTSIDE', 'ANGLE ON', 'MUSIC ON', 'MUSIC UP', 
		'CLOSE ON', 'THE END', 'CUT FROM', 'CAMERA', 'LENS', 'MINIATURE', 'ANGLE', 'POV', 
		'SUNSET', 'AERIAL VIEW', 'FANTASY', 'CLOSE UP', 'SLOW MOTION', 'CLOSE-UP', ' END ', ' END.'
		'DAY', 'NIGHT', 'MORNING', 'EVENING', 'WEEK', 'THE ', 'SCENE', 'ACTION', 'CONTINUED', 'CHANGED', 'HORIZON', 
		'ENDS', 'MONTAGE', 'FROM', 'WIDE-SHOT', 'SHOT', 'EXPLOSION', 'THEY', 'DISSOLVE', 'FOOTAGE',
		'CONTINUED', 'ROOM', 'UP AHEAD', 'SHOOTING SCRIPT', 'NEARBY', 'CUTS', 'SEES', 'INSERT', 'REVEAL'
	]

	reply_blacklist = [
		'LATER', 'FADE OUT', 'FADE IN', 'CUT TO', 'EXT.', 'EXTERIOR',
		'INT.', 'INTERIOR', 'ANGLE ON', 'MUSIC ON', 'MUSIC UP', 
		'CLOSE ON', 'THE END', 'CUT FROM', 'CAMERA', 'LENS', 'MINIATURE', 'ANGLE', 'POV', 
		'SUNSET', 'AERIAL VIEW', 'FANTASY', 'CLOSE UP', 'SLOW MOTION', 'CLOSE-UP', 'END ',
		' DAY', ' NIGHT', ' MORNING', 'WEEK', 'SCENE', 'CONTINUED', 'CHANGED', 'HORIZON', 
		'ENDS', 'MONTAGE', 'WIDE-SHOT', 'DISSOLVE', 'FILM INSET',
		'CONTINUED', 'ROOM', 'UP AHEAD', 'SHOOTING SCRIPT', 'NEARBY', 'CUTS', 'INSERT'
	]

	def parse(self, text):
		"""
		This method takes a movie script (str) as an input, and returns an instance of
		the Movie class, representing the movie.
		"""
		# Try to retrieve the character list
		characters = self._get_characters(text)

		# if there are less than the minimum number of characters, special case
		if len(characters) < self.minimum_characters:
			# identify special case stereotype
			characters = self._special_characters(text)

		# retrieve metadata
		title = self.get_title(text)
		author = self.get_author(text)
		genre = self.get_genre(text)

		# if it still doesn't work, warn user
		if len(characters) < self.minimum_characters:
			fix_string = "Please check the original file's formatting, or add a special case in ScriptParser's _special_characters() method."
			print("The script %s couldn't be parsed. %s" % (title, fix_string))
			error_movie = Movie(title, author, genre, "This script couldn't be parsed. %s" % fix_string)
			return error_movie
		else:
			# return instance of Movie
			movie = Movie(title, author, genre, characters)
			return movie
		

	def _get_characters(self, text):
		"""
		Input: correctly formatted movie script (str)
		Output: list of characters extracted from the script
		"""
		# group 1: character name, group 2: didascalie
		header_regex = re.compile(r"(?m)^[ \t]*([A-Z][A-Z0-9 -]+?)(\([\w'\.]+\))?$")
		# group 1: didascalie, group 2: reply text, group 3: final punctuation mark
		reply_regex = re.compile(r"(?m)^\s*(\([\w][\w '.,\n]+?\))?([\w\s,\.:;!?'\"-]+?(([!?.\"-]|(\.{3} ))\n))")

		characters = dict()
		
		matches = list(header_regex.finditer(text))
		for idx, m in enumerate(matches):
			char_name = m.group(1).strip()
			char_didascalie = m.group(2) if m.group(2) else ""
			
			# get segment substring: from end of this character header to the start
			# of the next one (or the end of the script if this is the last character header)
			if idx != len(matches)-1:
				next_match = matches[idx+1]
				segment = text[m.end():next_match.start()]
			else:
				segment = text[m.end():]

			# clean segment
			replies = list()

			reply_matches = list(reply_regex.finditer(segment))
			for idx, rm in enumerate(reply_matches):
				
				# reject matches after the first if they don't have a didascalie
				# may lead to loss of data, for instance if there is a punctuation mark
				# at the end of a line in the middle of a reply.
				# but it is an efficient way of rejecting all other text following a reply
				if idx > 0 and not rm.group(1):
					break
				
				# clean reply and didascalie
				didascalie = self._clean_padding((char_didascalie + " " + rm.group(1) if rm.group(1) else ""))
				reply_text = self._clean_padding(rm.group(2))

				# compute start and end positions of the reply 
				reply_start = m.end() + rm.start(2)
				reply_end = m.end() + rm.end(2)
				
				# store in dataclass
				reply = Reply(reply_text, didascalie, reply_start, reply_end)

				# store dataclass instance in the list of replies for this character
				replies.append(reply)
				
			# store in dataclasses
			if char_name not in characters:
				characters[char_name] = Character(char_name, replies)
			else:
				characters[char_name].Replies += replies

		# nettoyer liste personnages

		characters_list = self._clean_character_list(list(characters.values()))

		return characters_list

	def _special_characters(self, text):
		"""
		Input: strangely formatted movie script (str)
		Output: new character list generated by the appropriately modified movie script
		"""

		# Regex that matches script texts written out on a single line
		all_same_line = re.compile(r"^\s+.{1000}")

		# Regex that matches non-capitalized character names followed by a colon which may or may not be on the same line as their replies
		# groups 1, 3, 4: whitespace that needs to be retained, group 2: offending character name that needs to be modified
		colon = re.compile(r"(?m)^(\s*)([A-Za-z0-9 .-]+)(\s*):(\s*\n*)")

		# Regex that matches non-capitalized character names not followed by a colon
		# groups 1, 3: whitespace that needs to be retained, group 2: offending character name that needs to be modified
		no_colon = re.compile(r"(?m)^(\s*)([A-Za-z0-9]+)(\s*\n+)")

		fail = 10 # minimum matches a script needs to have in order to be sorted in a specific group
       
	   	# Matches first case: transforms any whitespace substrings larger than 3 into newline breaks readable by the parser
		matches = re.findall(all_same_line, text)
		if len(matches) == 1:
			return self._get_characters(re.sub(r"(\s{3,})", lambda clean: "\n" + clean.group(1)[:-1], text))

		# Matches second case: capitalizes capture group 2, removes the colon, forces a newline after the character name and retains all whitespace
		matches = re.findall(colon, text)
		if len(matches) > fail:
			return self._get_characters(re.sub(colon, lambda clean: clean.group(1) + clean.group(2).upper() + clean.group(3) + "\n" + clean.group(4), text))

		# Matches third case: capitalizes capture group 2, forces a newline after the character name and retains all whitespace
		matches = re.findall(no_colon, text)
		if len(matches) > fail:
			return self._get_characters(re.sub(no_colon, lambda clean: clean.group(1) + clean.group(2).upper() + "\n" + clean.group(3)[:-1], text)) 

		# Return an empty list in case none of the regex cases match
		return [] 

	def get_title(self, text):
		"""Finds the title of the movie"""
		title = re.findall(r"(?<=\t).+(?=\s+Writers :)", text)
		[el.replace("\u00a0", " ") for el in title]
		return title[0]

	def get_author(self, text):
		"""Finds a list of the movie's authors"""
		auteurs = re.findall(r"(?<=Writers : ).+(?=\n)", text)
		list_auteurs = auteurs[0].split("\u00a0")
		return [s for s in list_auteurs if s]

	def get_genre(self, text):
		"""Finds the list of the movie's genres"""
		genre = re.findall(r"(?<=Genres : ).+(?=\n)", text)
		list_genre = genre[0].split("\u00a0")
		return [s for s in list_genre if s]

	def _clean_padding(self, segment):
		"""Removes all extra padding and line breaks from a string. Returns a correctly formatted string"""
		return " ".join([l.strip() for l in segment.split("\n")]).strip()

	def _clean_character_list(self, charlist):
		# for each character, remove replies that contain bad words
		clean_charlist = list()

		for char in charlist:
			charname = char.Character
			keep_char = True

			clean_replies = list()
			for r in char.Replies:
				reply = r.Reply
				keep_reply = True

				# check if this reply satisfies all the conditions to be kept
				if (
					any([w in reply for w in self.reply_blacklist]) or 	# remove reply if any bad word is contained in it (case sensitive)
					re.search(r"\d+\.", reply)							# remove replies that contain a page number (numbers followed by a dot)
				):
					keep_reply = False
				
				if keep_reply:
					clean_replies.append(r)
			
			# overwrite character's replies list
			char.Replies = clean_replies

			# check if this character satisfies all the conditions to be kept
			if (
				len(char.Replies) < self.minimum_replies or					# remove characters that have less than the minimum number of replies
				any([w in charname for w in self.character_blacklist]) or 	# remove characters which have bad words in them indicating they're not characters
				charname.count(" ") > 5 or 									# remove characters whose name contains too many spaces
				re.search(r"[A-Z]\d+", charname) or							# removes lines identified as a character, when they are "B3" or "A337"
				(charname.startswith('(') and charname.endswith(')')) or
				charname.endswith(".") or
				charname.endswith(" -") or 
				charname.startswith("ON ") or 
				charname.startswith("BACK ") or
				charname.startswith("CUT ") or
				charname.startswith("TO ") or
				charname.startswith("A ") or
				charname.startswith("END ")
			):
				keep_char = False

			if keep_char:
				clean_charlist.append(char)

		return clean_charlist