'ACTOR_STATUS':
	if dict_string == "Fighting":
		if $AudioStreamPlayer.stream != load("res://audio/music/enneagon/19 Counterfeit Finale.ogg"):
			if $AudioStreamPlayer.stream == null:
				$AudioStreamPlayer.stream = load("res://audio/music/enneagon/19 Counterfeit Finale.ogg")
				$AudioStreamPlayer.play()
			elif $AudioStreamPlayer.stream != null:
				if $AudioStreamPlayer.stream != load("res://audio/music/enneagon/19 Counterfeit Finale.ogg"):
					$AudioStreamPlayer.stream = load("res://audio/music/enneagon/19 Counterfeit Finale.ogg")
					$AudioStreamPlayer.play()
				else:
					pass
			else:
				$AudioStreamPlayer.stream = load("res://audio/music/enneagon/19 Counterfeit Finale.ogg")
				$AudioStreamPlayer.play()

	if dict_string != "Fighting":
		if $AudioStreamPlayer.stream != load("res://audio/music/enneagon/10 Sure Is Dark In Here.ogg"):
			if $AudioStreamPlayer.stream == null:
				$AudioStreamPlayer.stream = load("res://audio/music/enneagon/10 Sure Is Dark In Here.ogg")
				$AudioStreamPlayer.play()
			elif $AudioStreamPlayer.stream != null:
				if $AudioStreamPlayer.stream != load("res://audio/music/enneagon/10 Sure Is Dark In Here.ogg"):
					$AudioStreamPlayer.stream = load("res://audio/music/enneagon/10 Sure Is Dark In Here.ogg")
					$AudioStreamPlayer.play()
				else:
					pass
			else:
				$AudioStreamPlayer.stream = load("res://audio/music/enneagon/10 Sure Is Dark In Here.ogg")
				$AudioStreamPlayer.play()