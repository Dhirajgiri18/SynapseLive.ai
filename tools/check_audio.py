import soundcard as sc


print("Default speaker:", sc.default_speaker())
print("Default mic:", sc.default_microphone())
for microphone in sc.all_microphones(include_loopback=True):
    loopback = " (loopback)" if microphone.isloopback else ""
    print(" -", microphone.name, loopback)
