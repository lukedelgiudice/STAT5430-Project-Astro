#pragma once

#include "CoreMinimal.h"
#include "CapTickReplayDriver.h"
#include "LayeredStatAggregator.h"
#include "LocationAggregatorVolume.h"
#include "GameMode/ArchiveChannel_Message.h"
#include "GameMode/ArchiveChannel_Performance.h"
#include "GameMode/NTGameMode.h"
#include "ReplayDriver_GameStats.generated.h"


class UNTPlayersConfig;

UCLASS()
class ASTROSTUDIES_API UReplayDriver_GameStats : public UCapTickReplayDriver
{
	GENERATED_BODY()

	FString MapName;

	TArray<FArchiveChannel_DeviceProfile> DeviceProfiles;
	TArray<FArchiveChannel_Performance> PerformanceSnapshots;
	TArray<FArchiveChannel_Message> ChatMessages;

private:
	TMap<FNetTickPlayerId, FString> OperatingPlayerMap;

	// Data
private:
	struct FPlayerData
	{
		FUniqueNetIdPtr NetId;
		uint32 NumKills = 0;
		uint32 NumDeaths = 0;
		FCapTickAvgAggregator AverageSpeed; 
		FCapTickAvgAggregator AverageMovingSpeed;
		uint32 NumPlayTicks = 0;
		uint32 NumTicksFloating = 0;
		uint32 NumTicksMagneting = 0;
		uint64 NumDashes = 0;
		uint64 NumDirectionalDashes = 0;
		uint64 NumKicks = 0;
		TArray<FString> PerfCSVLines;
	};
	
	FCapTickAvgAggregator AggregateAverageKillDistance;
	int TotalSpawns = 0;
	int TotalEliminations = 0;
	
	TMap<FString, FPlayerData> PlayerData;

	
	struct FItemData
	{
		uint32 NumTicksUsed = 0;
		uint32 NumTicksEquipped = 0;
		FCapTickAvgAggregator AverageKillDistance;
		uint32 NumKills = 0;
		uint32 NumDeaths = 0;
		uint32 NumKillsInInventory = 0;
		uint32 NumDeathsInInventory = 0;
	};
	TMap<TSubclassOf<UNetTickComponent>, FItemData> ItemData;

	uint32 ShurikenDropShotKills=0;
	uint32 ShurikenRegularShotKills=0;
	TMap<FNetTickPlayerId, int> PrevAstronautHealthMap;
	TArray<uint8> RipperBulletsInClipAtKill;

	TMap<FNetTickNodeId, FVector> SwordStartStabLocation;

	FCapTickAvgAggregator AverageSwordStabKillDistance;

	FLocationAggregatorVolume LocationAggregatorVolume;


	bool bReachedEndCondition;


// public:
// 	struct FPendingFightData
// 	{
// 		float RemainingTime;
// 		uint32 StartStamp;
// 	};
// 	TMap<FNetTickPlayerId, FPendingFightData> PendingFights;
//
// 	struct FPlayerPair
// 	{
// 		FNetTickPlayerId A;
// 		FNetTickPlayerId B;
// 		friend FORCEINLINE uint32 GetTypeHash(const FPlayerPair& Key) { return GetTypeHash(Key.A) + GetTypeHash(Key.B); }
// 		bool operator==(const FPlayerPair& Other) const { return (A == Other.A && B == Other.B) || (A == Other.B && B == Other.A); }
// 	};
// 	struct FFightData
// 	{
// 		float RemainingTime;
// 		uint32 EndStamp;
// 	};
// 	TMap<FPlayerPair, FFightData> OngoingFights;


	struct FPlayerUpdateData
	{
		uint32 Stamp;
		FNetTickPlayerId PlayerId;
		uint8 Health;
		FVector Location;
		FRotator Rotation;
		FVector Velocity;
	};

	TArray<FPlayerUpdateData> PlayerUpdateData;
	

public:
	TArray<TSharedPtr<FJsonObject>> JsonEventList;

public:
	TSharedPtr<FJsonObject> GameJson;

public:
	void InitLocationAggregator(const UNetTickWorld* BaseWorld);
	virtual void Init(const UNetTickWorld* BaseWorld) override;
	virtual void CustomChannelDeserialize(uint8 ChannelId, FBitReader& EntryReader) override;
	void HandleEliminationEvent(const UNetTickWorld* World, const FNetTickEvent& Event);
	void HandleDamageEvent(const UNetTickWorld* World, const FNetTickEvent& Event);
	void OnPushEvent(const UNetTickWorld* World, const FNetTickEvent& Event);
	virtual void OnSimulatedTick(const UNetTickWorld* Tick) override;
	void FinalizeGameJson();
	virtual void Shutdown() override;
};
