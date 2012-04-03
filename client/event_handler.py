from __future__ import division, print_function

# add our main folder as include dir
import sys
sys.path.append("../")

import struct
import engine.map
import engine.player
import function, constants
from networking import event_serialize


def Server_Event_Hello(client, networker, game, event, packet_sequence):
    # Stop saying hello
    networker.has_connected = True
    # TODO: Some version check using event.version and constants.GAME_VERSION_NUMBER
    # Set all the important values to the game
    game.servername = event.servername
    player_id = event.playerid
    game.maxplayers = event.maxplayers
    game.map = engine.map.Map(game, event.mapname)
    client.start_game(player_id)

def Server_Event_Player_Join(client, networker, game, event, packet_sequence):
    newplayer = engine.player.Player(game, game.current_state, event.id)
    newplayer.name = event.name

def Server_Event_Changeclass(client, networker, game, event, packet_sequence):
    player = game.current_state.players[event.playerid]
    player.nextclass = function.convert_class(event.newclass)

def Server_Event_Die(client, networker, game, event, packet_sequence):
    player = game.current_state.players[event.playerid]
    character = game.current_state.entities[player.character_id]
    character.die(game, game.current_state)

def Server_Event_Spawn(client, networker, game, event, packet_sequence):
    player = game.current_state.players[event.playerid]
    player.spawn(game, game.current_state)

def Server_Snapshot_Update(client, networker, game, event,  packet_sequence):
    # Copy the current game state, and replace it with everything the server knows
    state = game.current_state

    # Rewind the state back to before the compensation
    state.update(game, -networker.latency*constants.INPUT_SEND_FPS)

    for player in state.players.values():
        length = player.deserialize_input(event.bytestr)
        event.bytestr = event.bytestr[length:]

        try:
            character = state.entities[player.character_id]
            length = character.deserialize(state, event.bytestr)
            event.bytestr = event.bytestr[length:]
        except KeyError:
            # Character is dead
            pass
    # Update this state with all the input information that appeared in the meantime
    for i in range(networker.latency):
        try:
            inputstr = networker.inputlog[packet_sequence+i]
            player = state.players[client.our_player_id]
            player.deserialize(state, inputstr)
        except:
            pass
        state.update(game, constants.INPUT_SEND_FPS)

def Server_Full_Update(client, networker, game, event, packet_sequence):
    numof_players = struct.unpack_from(">B", event.bytestr)[0]
    event.bytestr = event.bytestr[1:]

    for index in range(numof_players):
        player = engine.player.Player(game, game.current_state, index)

        player.name, player_class, character_exists = struct.unpack_from(">32pBB", event.bytestr)
        player.nextclass = function.convert_class(player_class)
        event.bytestr = event.bytestr[34:]

        if character_exists:
            player.spawn(game, game.current_state)

def Server_Event_Disconnect(client, networker, game, event, packet_sequence):
    player = game.current_state.players[event.playerid]
    print (player.name +" has disconnected")
    player.destroy(game, game.current_state)

# Gather the functions together to easily be called by the event ID
eventhandlers = {}
eventhandlers[constants.EVENT_HELLO] = Server_Event_Hello
eventhandlers[constants.EVENT_PLAYER_JOIN] = Server_Event_Player_Join
eventhandlers[constants.EVENT_PLAYER_CHANGECLASS] = Server_Event_Changeclass
eventhandlers[constants.EVENT_PLAYER_DIE] = Server_Event_Die
eventhandlers[constants.EVENT_PLAYER_SPAWN] = Server_Event_Spawn
eventhandlers[constants.SNAPSHOT_UPDATE] = Server_Snapshot_Update
eventhandlers[constants.FULL_UPDATE] = Server_Full_Update
eventhandlers[constants.EVENT_PLAYER_DISCONNECT] = Server_Event_Disconnect
