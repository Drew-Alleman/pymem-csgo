import time
import pymem
import requests 
import win32api

try:
    hazedumper = requests.get("https://raw.githubusercontent.com/frk1/hazedumper/master/csgo.json").json()
except requests.RequestException:
    exit("[-] Failed to fetch the latests offsets from hazedumper!")

# Open CSGO in pyMem
csgo = pymem.Pymem("csgo.exe")
# Load client.dll and get the module base address 
module_base = pymem.process.module_from_name(csgo.process_handle, "client.dll").lpBaseOfDll

if not module_base:
    exit("[-] Failed to load module: 'client.dll'")

class CEntity:
    """ CSGO Entity class 
    Used to control and monitor player entites in CSGO
    """
    def __init__(self, address) -> None:
        """ Defines a CSGO Player Entity
        :param address: Memory address of entity
        """
        self.address = address

    def get_health(self) -> int:
        """ Fetches the entitys current health
        :return: Entity's Health
        """
        return csgo.read_int(self.address + hazedumper["netvars"]["m_iHealth"])

    def is_alive(self) -> bool:
        """ Checks to see if the current entity is alive
        :return: True if the entity is alive
        """
        return self.get_health() != 0

    def is_dormant(self) -> bool:
        """ Checks to see if the player is AFK / Too far away
        :return: True if the current entity is dormant
        """
        return csgo.read_bool(self.address + hazedumper["signatures"]["m_bDormant"])
    
    def get_team_number(self) -> int:
        """ Gets the current entities team number
        :return int: Team number
        2 -> Terroist
        3 -> Counter-terrorist
        """
        return csgo.read_int(self.address + hazedumper["netvars"]["m_iTeamNum"])

    def spot(self) -> None:
        """ Used to set the entity as spotted on the radar
        """
        csgo.write_bool(self.address + hazedumper["netvars"]["m_bSpotted"], True)

    def is_defusing(self) -> bool:
        """ Checks to see if the current player is defusing
        :return: True if the player is defusing
        """
        return csgo.read_bool(self.address + hazedumper["netvars"]["m_bIsDefusing"])

    def glow(self, r: float, g:float, b: float, a:float = 1):
        """ Applies glow to an entity
        """
        glow_manager = csgo.read_int(module_base + hazedumper["signatures"]["dwGlowObjectManager"])
        entity_glow = csgo.read_int(self.address + hazedumper["netvars"]["m_iGlowIndex"])
        entity = glow_manager + entity_glow * 0x38
        csgo.write_float(entity +  0x8, float(r))  # R
        csgo.write_float(entity + 0xC, float(g))   # G
        csgo.write_float(entity + 0x10, float(b))  # B
        csgo.write_float(entity + 0x14, float(a))  # Alpha
        csgo.write_bool(entity + 0x28, True)       # Enable glow

    def glow_by_health(self) -> None:
        """ Glows the entity depending on how much health they have 
        """
        entity_health = self.get_health()
        if entity_health < 30:
            self.glow(1, 0, 0) # Glow Red
        elif entity_health < 50:
            self.glow(1, 1, 0) # Glow yellow
        else:
            self.glow(0, 1, 0) # Glow green

class LocalPlayer(CEntity):
    def update(self):
        self.address = csgo.read_int(module_base + hazedumper["signatures"]["dwLocalPlayer"])

def main() -> None:
    localplayer = LocalPlayer(None)
    while True:
        localplayer.update()
        if win32api.GetKeyState(117): # Kill switch (F6)
            break
        while localplayer.address <= 0: # If the localplayer address is not a valid
            localplayer.update()
            time.sleep(1.5)
        # Loop through all player entities
        for i in range(0, 32):
            if not localplayer.is_alive():
                break
            entity = csgo.read_int(module_base + hazedumper["signatures"]["dwEntityList"] + i * 0x10)
            if not entity or entity <= 0: # If the entity is not a valid memory address
                continue
            c_entity = CEntity(entity)
            if not c_entity.is_alive() or c_entity.is_dormant(): # If entity is either dead or AFK / Too far away
                continue 
            if c_entity.get_team_number() == localplayer.get_team_number():
                c_entity.glow(0, 0, 1) # Glow blue
                continue # Don't need to spot them on the radar
            elif c_entity.is_defusing():
                # Glow purple
                c_entity.glow(1, 0, 1)
            else:
                # Glow depending on there health
                c_entity.glow_by_health()
            c_entity.spot()
        time.sleep(.05)
    print("[*] Stopping CSGO cheats")       

if __name__ == '__main__':
    print("[*] Started CSGO cheats")
    main()
