import sys
import request_worker as rw
import json, re

def GetDetectWordsList(filePath: str) -> list:
    
    detectWordsList = list()
    
    with open(filePath, "r") as detectWordsListFile:
        
        detectWordsList.extend(detectWordsListFile.readlines())

    return detectWordsList        

def ReadCredentialsJSON():
    """ Reads json file of credentials """
    credentials = json.load(open(rw.cdir + "/credentials.json", "r"))
    return credentials

def GetHeadersByCredentialsJSON():
    """ Generate headers dict by credentials from JSON """    
    
    credentials = ReadCredentialsJSON()
    
    headers = \
    {
        'Content-Type': 'application/json',
        'X-API-Authorization': f'Bearer {credentials["BEARER"]}',
        'x-api-key': credentials["KEY"],
        'x-api-fingerprint': credentials["FINGERPRINT"],
        'cache-control': 'no-cache',
        'x-api-workspace-id': credentials['WORKSPACE']
    }
    
    return headers

def GetActInfo(actId: int) -> dict:
    """ Function requests ProtoBrain for ActInfo by ActID and return that """
        
    full_act_url = f"act/{actId}/expanded"
    full_act = rw.request(
            url=full_act_url, type=rw.ReqType.GET).json()
    
    return full_act
    
def GetProcessingStatuses(actInfo: dict) -> dict:
    """ That function make easy access to processing statuses"""
    return actInfo["act"]["data"]["processing"]["jobs"]

def GetTranscribationPlatform(actId: int, provider: str) -> dict:
    """ Function requests ProtoBrain for act transcribation and then trying to get target provider transcribation """
    
    get_transcribation_url  = f'act/{actId}/data_layer/transcription?include_items=1'
    transcribations = rw.request(
                    url=get_transcribation_url, type=rw.ReqType.GET).json()
       
    for datalayerItem in transcribations["data"]:
        if len(datalayerItem["data_layer_items"]) > 0:
            
            datalayerItems = datalayerItem["data_layer_items"][0]
            
            if datalayerItems.get("provider_id", "None") == provider:
                return datalayerItems
        
    return dict()
    

def GetDiarization(actId: int) -> dict:
    """ Function requests ProtoBrain for diarization data """
    
    get_diarization_url = f'act/{actId}/data_layer/speaker_diarisation?include_items=1'
    diarization = rw.request(
                    url=get_diarization_url, type=rw.ReqType.GET).json()

    if "data" in diarization:
        if len(diarization["data"]) > 0:
            if "data_layer_items" in diarization["data"][0]:
                return diarization["data"][0]["data_layer_items"][0]

    return dict()

def RepresentDiarization(diarization: dict) -> dict:
    """ Function converts ProtoBrain diarization struct to more usefull representation of it"""
    
    representedDiarization = dict()
    
    for speaker in diarization["speakers"]:
        representedDiarization.update({
            speaker["speaker_id"] : speaker["partitions"]
        })
        
    return representedDiarization
    

def GetWordsToDiarization(transcribation, diarization : dict) -> dict:
    """ Function extracts transcribation from diarization time segments of speakers """
    
    diarizationRepr = RepresentDiarization(diarization)
    
    for speaker_id in diarizationRepr:
        
        for phrase in diarizationRepr[speaker_id]:
            
            phraseWords = filter(lambda x: x["start"] >= phrase["start"] and x["start"] <= phrase["end"], transcribation["words"])
            phrase.update(dict(words = list(phraseWords)))
        
    return diarizationRepr
            

def ClearWord(word : str) -> str:
    
    return re.sub(r'[^\s\w]', "", word).lower()
    

def FindWordsToSpeaker(wordsList : list, diarizationRepresent : dict) -> dict:
    """ Function extracts words per speaker time segments which contains in wordsList """
    
    wordsDetects = dict()
    
    for speaker_id in diarizationRepresent:
        
        wordsDetects.update({ speaker_id : list() })
        
        for phrase in diarizationRepresent[speaker_id]:
                       
            phraseWords = list([phraseWord for phraseWord in phrase["words"] if 
                                   len(list([detectWord for detectWord in wordsList 
                                             if ClearWord(detectWord) == ClearWord(phraseWord["word"])])) > 0])
            
            wordsDetects[speaker_id].extend(phraseWords)  
                   
    return wordsDetects
            
    

def Main():
    
    actId = int(sys.argv[1])
    wordsToDetect = GetDetectWordsList(sys.argv[2])
    
    rw.PB_HEADERS = GetHeadersByCredentialsJSON()
       
    actInfo = GetActInfo(actId)
    processingStatuses = GetProcessingStatuses(actInfo)
       
    # Verify if processing has done
    
    if(processingStatuses["transcription"]["tinkoff"]["status"] != "finished"):
        print("ERROR: Tinkoff transcribation has not finished!")
        exit(0)
        
    if(processingStatuses["diarization"]["kaldi"]["status"] != "finished"):
        print("ERROR: Diarization has not finished!")
        exit(0)
    
    # Get data
    
    tinkoffTranscribation = GetTranscribationPlatform(actId, "tinkoff")
    diarization = GetDiarization(actId)
    
    # Make 1st data post-processing
    
    diarizationRepr = GetWordsToDiarization(tinkoffTranscribation, diarization)
    
    # Find words detect and create Scenes(with Scene Datalayers)
        
    wordsDetect = FindWordsToSpeaker(wordsToDetect, diarizationRepr)
    
    for speaker_id in wordsDetect:
        
        # Creating Scene Datalayer(container of scenes)
        sceneDatalayerId = rw.create_data_layer(actId = actId, comment =  "Найденные слова " + speaker_id)
        
        for badWordEntry in wordsDetect[speaker_id]:
            
            # Creating scenes
            rw.create_scene(datalayerId = sceneDatalayerId, comment = badWordEntry["word"], sbeg = badWordEntry["start"], send = badWordEntry["end"], color = "#d7d7d7")


if __name__ == "__main__":
    Main()