#include "ReplayDriver_GameStats.h"

#include "AstroStudies.h"
#include "NetTickGameState.h"
#include "NetTickUtil.h"
#include "NTGameMode_GunGame.h"
#include "NTInstigationTracker.h"
#include "OnlineSubsystem.h"
#include "OnlineSubsystemUtils.h"
#include "Astronaut/NTActionDriver.h"
#include "Astronaut/NTAstronaut.h"
#include "AstroRifle/NTAstroRifleRemote.h"
#include "Dash/NTDash.h"
#include "Effects/NTModifyPlayerDataEffect.h"
#include "FreeForAll/NTGameMode_FreeForAll.h"
#include "GameMode/ArchiveChannel_Message.h"
#include "GameMode/ArchiveChannel_Performance.h"
#include "GameMode/AstroGameMode.h"
#include "GameMode/GameModeDefinition.h"
#include "GameMode/NTGameMode.h"
#include "GameMode/NTGameMode_King.h"
#include "GameMode/NTPlayersConfig.h"
#include "Items/Boomerang/NTBoomerangRemote.h"
#include "Items/Grapple/NTGrapple.h"
#include "Items/Gun/NTGun.h"
#include "Items/Net/NTNetRemote.h"
#include "Items/RocketLauncher/NTRocketLauncherRemote.h"
#include "Items/Sword/NTSwordRemote.h"
#include "Items/TeleportGrenade/NTTeleportRemote.h"
#include "Items/ThrowingStar/NTThrowingStarRemote.h"
#include "MagKick/NTMagKick.h"
#include "Magnet/NTMagnet.h"
#include "Melee/NTMelee.h"
#include "Nightshade/NTNightshade.h"
#include "Nightshade/NTNightshadeRemote.h"
#include "Physics/NTPhzEngine.h"
#include "QuadCannon/NTQuadCannonRemote.h"
#include "Ripper/NTRipperRemote.h"
#include "Sledge/NTSledge.h"
#include "Sledge/NTSledgeRemote.h"
#include "Spark/NTSparkRemote.h"
#include "TeamDeathmatch/NTGameMode_TeamDeathmatch.h"


TSharedPtr<FJsonValue> FloatToJson(float Value, int Decimals = 3)
{
	return MakeShared<FJsonValueNumberString>(ASTRO::RoundFloatToString(Value, Decimals));
}
TSharedPtr<FJsonValue> VecToJson(FVector Value, int Decimals = 3)
{
	TArray<TSharedPtr<FJsonValue>> Array;
	Array.Add(FloatToJson(Value.X, Decimals));
	Array.Add(FloatToJson(Value.Y, Decimals));
	Array.Add(FloatToJson(Value.Z, Decimals));
	return MakeShared<FJsonValueArray>(Array);
}
TSharedPtr<FJsonValue> DirToJson(FVector Value)
{
	FRotator Rotator = FRotationMatrix::MakeFromX(Value).Rotator();
	TArray<TSharedPtr<FJsonValue>> Array;
	Array.Add(FloatToJson(Rotator.Pitch, 0));
	Array.Add(FloatToJson(Rotator.Yaw, 0));
	return MakeShared<FJsonValueArray>(Array);
}



static bool IsRangedWeapon(UClass* Class)
{
	return 	Class == UNTAstroRifleRemote::StaticClass() ||
			Class == UNTBoomerangRemote::StaticClass() ||
			Class == UNTNightshadeRemote::StaticClass() ||
			Class == UNTQuadCannonRemote::StaticClass() ||
			Class == UNTRipperRemote::StaticClass() ||
			Class == UNTRocketLauncherRemote::StaticClass() ||
			Class == UNTSledgeRemote::StaticClass() ||
			Class == UNTSparkRemote::StaticClass() ||
			Class == UNTThrowingStarRemote::StaticClass();
}


FString NodeClassToString(const UClass* Class)
{
	FString Name = Class->GetName();
	if (Name.StartsWith("NT")) Name.RightChopInline(2);
	if (Name.EndsWith("Remote")) Name.LeftChopInline(6);
	return Name;
}

void UReplayDriver_GameStats::InitLocationAggregator(const UNetTickWorld* BaseWorld)
{
	struct FMapLocationDef
	{
		FTransform Transform;
		FVector Size;
		float Resolution;
	};
	const static TMap<FString, FMapLocationDef> MapToLocationBounds = {
		{ "Outpost", { FTransform(FQuat::Identity, FVector(-3900, -3800, -1200)), FVector(3500+3900,1200+3800,3300+1200), 50.f } }, // 5MB
		{ "Observatory", { FTransform(FQuat::Identity, FVector(-7500, -4100, -600)), FVector(6700+7500, 5000+4100, 1200+600), 50.f } }, // 7MB
		{ "Prison", { FTransform(FQuat::Identity, FVector(-6500, -2200, -500)), FVector(4600+6500,4000+2200, 1300+2200), 50.f } }, // 7MB
		{ "Stadium", { FTransform(FQuat::Identity, FVector(-2200, -5000, -4000)), FVector(9500+2200, 6600+5000, 5000+4000), 100.f } } // 5MB
	};
	if (ensureAlways(MapToLocationBounds.Contains(BaseWorld->GetMapName())))
	{
		FMapLocationDef MapLocDef = MapToLocationBounds[BaseWorld->GetMapName()];
		LocationAggregatorVolume = FLocationAggregatorVolume(MapLocDef.Transform, MapLocDef.Size, MapLocDef.Resolution); 	
	}
}

void UReplayDriver_GameStats::Init(const UNetTickWorld* BaseWorld)
{
	Super::Init(BaseWorld);

	TotalSpawns = 0;
	TotalEliminations = 0;
	bReachedEndCondition = false;
	
	IOnlineIdentityPtr IdentityInterface = Online::GetSubsystem(GetWorld()) ? Online::GetSubsystem(GetWorld())->GetIdentityInterface() : nullptr;

	MapName = BaseWorld->GetMapName();

	PerformanceSnapshots.Sort([](const FArchiveChannel_Performance& A, const FArchiveChannel_Performance& B){ return A.Stamp < B.Stamp; });

	GameState->GetNetTickSimulator()->OnPushEvent.BindUObject(this, &ThisClass::OnPushEvent);

	OperatingPlayerMap.Reset();

	UE_LOG(LogAstroStudy, Display, TEXT("OnStartReplay %llu"), Header.GameId)


	GameJson = MakeShared<FJsonObject>();

	FString GameModeName = GetWorld()->GetAuthGameMode()->GetClass()->GetName();
	if (AAstroGameMode* GameMode = GameState->GameModeClass->GetDefaultObject<AAstroGameMode>())
	{
		if (GameMode->GetGameModeData())
		{
			GameModeName = GameMode->GetGameModeData()->DisplayName.ToString();
		}
	}
	GameJson->SetStringField(TEXT("GameId"), FString::Printf(TEXT("%llu"), Header.GameId));
	GameJson->SetStringField(TEXT("StartUnixTimestamp"), FString::Printf(TEXT("%llu"), Header.StartUnixTimestamp));
	
	GameJson->SetStringField(TEXT("GameMode"), GameModeName);

	int GameDurationSeconds = FMath::TruncToInt(NetTickUtil::GetTimeBetweenStamps(InputBuffer.GetOldestStamp(), InputBuffer.GetNewestStamp()));
	GameJson->SetNumberField(TEXT("DurationSec"), GameDurationSeconds);

	GameJson->SetStringField(TEXT("Map"), BaseWorld->GetMapName());

	TSet<FString> Usernames;
	for (const auto& JoinEvents : PlayerJoinBuffer.GetData())
	{
		for (const auto& Join : JoinEvents.Value)
		{
			PlayerData.Add(Join.Username, {});
			
			Usernames.Add(Join.Username);

			TSharedPtr<FJsonObject> JsonEvent = MakeShared<FJsonObject>();
			JsonEvent->SetStringField("name", "join");
			JsonEvent->SetNumberField(TEXT("stamp"), Join.Stamp);
			
			JsonEvent->SetStringField(TEXT("username"), Join.Username);
			JsonEvent->SetNumberField(TEXT("id"), Join.PlayerId.GetIndex());
			if (IdentityInterface)
			{
				if (FUniqueNetIdPtr RecreatedNetId = IdentityInterface->CreateUniquePlayerId((uint8*)Join.NetId, FCapTickArchive::FPlayerJoin::NetIdSize))
				{
					JsonEvent->SetStringField(TEXT("net_id"), RecreatedNetId->ToString());
				}
			}
			JsonEventList.Add(JsonEvent);
		}
	}
	for (const auto& LeaveEvent : PlayerLeaveBuffer.GetData())
	{
		for (const auto& Leave : LeaveEvent.Value)
		{
			TSharedPtr<FJsonObject> JsonEvent = MakeShared<FJsonObject>();
			JsonEvent->SetStringField(TEXT("name"), "leave");
			JsonEvent->SetNumberField(TEXT("stamp"), Leave.Stamp);
			JsonEvent->SetNumberField(TEXT("id"), Leave.PlayerId.GetIndex());
			JsonEventList.Add(JsonEvent);
		}
	}
	for (const FArchiveChannel_Message& Message : ChatMessages)
	{
		TSharedPtr<FJsonObject> JsonEvent = MakeShared<FJsonObject>();
		JsonEvent->SetStringField("name", "chat");
		JsonEvent->SetNumberField("stamp", Message.Stamp);
		JsonEvent->SetStringField("sender", Message.Sender);
		JsonEvent->SetStringField("message", Message.Message);
		JsonEventList.Add(JsonEvent);
	}



	for (const auto& EventStamp : PlayerJoinBuffer.GetAllBeforeOrAt(BaseWorld->GetStamp()))
	{
		for (const auto& Join : EventStamp)
		{
			if (ensureAlways(!OperatingPlayerMap.Contains(Join.PlayerId)))
			{
				OperatingPlayerMap.Add(Join.PlayerId, Join.Username);

				// if (BasePlayerConfig->HasPlayer(Join.PlayerId))
				// {
				// 	BasePlayerConfig->GetLoadout(Join.PlayerId);
				// }
			}
		}
	}

	ItemData.Add(UNTAstroRifleRemote::StaticClass(), {});
	ItemData.Add(UNTBoomerangRemote::StaticClass(), {});
	ItemData.Add(UNTGrapple::StaticClass(), {});
	ItemData.Add(UNTNetRemote::StaticClass(), {});
	ItemData.Add(UNTNightshadeRemote::StaticClass(), {});
	ItemData.Add(UNTQuadCannonRemote::StaticClass(), {});
	ItemData.Add(UNTRipperRemote::StaticClass(), {});
	ItemData.Add(UNTRocketLauncherRemote::StaticClass(), {});
	ItemData.Add(UNTSledgeRemote::StaticClass(), {});
	ItemData.Add(UNTSparkRemote::StaticClass(), {});
	ItemData.Add(UNTSwordRemote::StaticClass(), {});
	ItemData.Add(UNTTeleportRemote::StaticClass(), {});
	ItemData.Add(UNTThrowingStarRemote::StaticClass(), {});


	InitLocationAggregator(BaseWorld);

	const UNTPlayersConfig* BasePlayerConfig = BaseWorld->GetConfig<UNTPlayersConfig>();
	
	for (FNetTickPlayerId PlayerId : BasePlayerConfig->GetPlayerIds())
	{
		TArray<UClass*> Loadout = BasePlayerConfig->GetLoadout(PlayerId);
		
		TSharedPtr<FJsonObject> SelectLoadoutEvent = MakeShared<FJsonObject>();
		SelectLoadoutEvent->SetStringField("name", "set_loadout");
		SelectLoadoutEvent->SetNumberField("stamp", BaseWorld->GetStamp());
		
		SelectLoadoutEvent->SetNumberField("player", PlayerId.GetIndex());
		TArray<TSharedPtr<FJsonValue>> LoadoutArray;
		for (UClass* Class : Loadout)
		{
			LoadoutArray.Add(MakeShared<FJsonValueString>(NodeClassToString(Class)));
		}
		SelectLoadoutEvent->SetArrayField("items", LoadoutArray);
		
		JsonEventList.Add(SelectLoadoutEvent);
	}
}

void UReplayDriver_GameStats::CustomChannelDeserialize(uint8 ChannelId, FBitReader& EntryReader)
{
	Super::CustomChannelDeserialize(ChannelId, EntryReader);

	if (ChannelId == FArchiveChannel_DeviceProfile::CHID)
	{
		FArchiveChannel_DeviceProfile Prof;
		Prof.Serialize(EntryReader, nullptr);
		DeviceProfiles.Add(Prof);
	}
	else if (ChannelId == FArchiveChannel_Performance::CHID)
	{
		FArchiveChannel_Performance Perf;
		Perf.Serialize(EntryReader, nullptr);
		PerformanceSnapshots.Add(Perf);
	}
	else if (ChannelId == FArchiveChannel_Message::CHID)
	{
		FArchiveChannel_Message Message;
		Message.Serialize(EntryReader, nullptr);
		ChatMessages.Add(Message);
	}
}

static FNetTickPlayerId GetEventPlayer(const FNetTickEvent& Event, const UNetTickWorld* World)
{
	if (const UNetTickComponent* NTComp = World->GetNode<UNetTickComponent>(Event.NodeId))
	{
		if (UNTAstronaut* NTAstronaut = NTComp->GetSibling<UNTAstronaut>())
		{
			return *NTAstronaut->OwningPlayerId;
		}
	}
	if (Event.EntityId && World->HasEntity(*Event.EntityId))
	{
		if (UNTAstronaut* NTAstronaut = World->GetFirstComponentOfClass<UNTAstronaut>(*Event.EntityId))
		{
			return *NTAstronaut->OwningPlayerId;
		}
		else
		{
			return *World->GetSystem<UNTInstigationTracker>()->GetSourcePlayer(*Event.EntityId);
		}
	}
	return FNetTickPlayerId();
}
void UReplayDriver_GameStats::HandleEliminationEvent(const UNetTickWorld* World, const FNetTickEvent& Event)
{
	TotalEliminations++;
	
	const FNTGameModeEliminationEventData& ElimData = Event.Data.Get<FNTGameModeEliminationEventData>();
	const FVector DeathLocation = World->GetSystem<UNTPhzEngine>()->GetLocation(*Event.EntityId);

	TSharedPtr<FJsonObject> ElimEventJson = MakeShared<FJsonObject>();
	ElimEventJson->SetStringField("name", "elim");
	ElimEventJson->SetNumberField("stamp", Event.Stamp);
	
	ElimEventJson->SetNumberField("target", ElimData.Target.GetIndex());
	if (ElimData.CauseChain.HasPlayer())
	{
		ElimEventJson->SetNumberField("instigator", ElimData.CauseChain.GetPrimaryPlayer().GetIndex());
	}
	if (ElimData.CauseChain.HasEntity())
	{
		ElimEventJson->SetStringField("causer", ElimData.CauseChain.GetPrimaryEntity().ToString(World));
	}
	if (ElimData.CauseChain.GetFirstChain().HasNode())
	{
		ElimEventJson->SetStringField("node", ElimData.CauseChain.GetFirstChain().GetPrimaryNode().ToString(World));
	}
	for (UNetTickComponent* Component : ElimData.CauseChain.GetPrimaryNodes<UNetTickComponent>(World))
	{
		if (ItemData.Contains(Component->GetClass()))
		{
			ElimEventJson->SetStringField("item", NodeClassToString(Component->GetClass()));
			break;
		}
	}
	JsonEventList.Add(ElimEventJson);

	UNTActionDriver* DeadAstronautActionDriver = World->GetFirstComponentOfClass<UNTActionDriver>(*Event.EntityId);
	TOptional<FNTEntityAction> EquipItemAction = DeadAstronautActionDriver->GetActiveActionInChannel(AAC_EquipItem); 
	for (UNetTickComponent* Component : World->GetComponents(*Event.EntityId))
	{
		if (ItemData.Contains(Component->GetClass()))
		{
			if (EquipItemAction.IsSet() && EquipItemAction->Instigator == Component->GetNodeId())
			{
				ItemData[Component->GetClass()].NumDeaths++;
			}
			ItemData[Component->GetClass()].NumDeathsInInventory++;
		}
	}

	if (OperatingPlayerMap.Contains(ElimData.Target))
	{
		FPlayerData& PD = PlayerData[OperatingPlayerMap[ElimData.Target]];
		PD.NumDeaths++;
	}

	if (ElimData.CauseChain.HasPlayer() && OperatingPlayerMap.Contains(ElimData.CauseChain.GetPrimaryPlayer()))
	{
		FPlayerData& PD = PlayerData[OperatingPlayerMap[ElimData.CauseChain.GetPrimaryPlayer()]];
		PD.NumKills++;
	}

	for (UNetTickComponent* Component : ElimData.CauseChain.GetPrimaryNodes<UNetTickComponent>(World))
	{
		if (ItemData.Contains(Component->GetClass()))
		{
			FItemData& ID = ItemData[Component->GetClass()];
			ID.NumKills++;

			FNetTickEntityId Astronaut = Component->GetEntityId();
			FVector KillerLocation = World->GetSystem<UNTPhzEngine>()->GetLocation(Astronaut);
			double KillDistance = FVector::Dist(KillerLocation, DeathLocation);

			if (UNTSwordRemote* SwordRemote = Cast<UNTSwordRemote>(Component))
			{
				if (SwordRemote->Stage == ESwordStage::Stab)
				{
					if (ensureAlways(SwordStartStabLocation.Contains(Component->GetNodeId())))
					{
						KillDistance = FVector::Dist(SwordStartStabLocation[Component->GetNodeId()], DeathLocation);
						AverageSwordStabKillDistance.AddValue(KillDistance);
					}
				}
			}
				
			ID.AverageKillDistance.AddValue(KillDistance);
			if (IsRangedWeapon(Component->GetClass()))
			{
				AggregateAverageKillDistance.AddValue(KillDistance);
			}

			for (UNetTickComponent* C : World->GetComponents(Astronaut))
			{
				if (ItemData.Contains(C->GetClass()))
				{
					ItemData[C->GetClass()].NumKillsInInventory++;
				}
			}
				
			if (const UNTRipperRemote* RipperRemote = Cast<UNTRipperRemote>(Component))
			{
				if (const UNTGun* Gun = RipperRemote->GetGun())
				{
					RipperBulletsInClipAtKill.Add(static_cast<uint8>(Gun->Ammo));
				}
			}

			if (const UNTThrowingStarRemote* TSRemote = Cast<UNTThrowingStarRemote>(Component))
			{
				if (ElimData.CauseChain.HasEntity() && World->GetSystem<UNTProjectileSystem>()->HasProjectile(ElimData.CauseChain.GetPrimaryEntity()))
				{
					bool bRegularShot = World->GetSystem<UNTProjectileSystem>()->GetProjectile(ElimData.CauseChain.GetPrimaryEntity()).Damage == 5;
					if (bRegularShot)
					{
						ShurikenRegularShotKills++;
					}
					else
					{
						ShurikenDropShotKills++;
					}
				}
			}
		}
	}
}

void UReplayDriver_GameStats::HandleDamageEvent(const UNetTickWorld* World, const FNetTickEvent& Event)
{
	if (!Event.EntityId) return;
	const UNTAstronaut* NTAstronaut = World->GetFirstComponentOfClass<UNTAstronaut>(*Event.EntityId);
	if (!NTAstronaut || !NTAstronaut->OwningPlayerId) return;

	const FNTDamageEventData& DmgData = Event.Data.Get<FNTDamageEventData>();
	
	{
		TSharedPtr<FJsonObject> JsonDamageEvent = MakeShared<FJsonObject>();
		JsonDamageEvent->SetStringField("name", "damage");
		JsonDamageEvent->SetNumberField("stamp", Event.Stamp);

		JsonDamageEvent->SetNumberField("target",  NTAstronaut->OwningPlayerId->GetIndex());
		JsonDamageEvent->SetNumberField("damage", DmgData.Damage);
		JsonDamageEvent->SetNumberField("prev_health", World->GetSystem<UNTHealthManager>()->GetHealth(*Event.EntityId));
		
		if (DmgData.Cause.HasPlayer())
		{
			JsonDamageEvent->SetNumberField("instigator",  DmgData.Cause.GetPrimaryPlayer().GetIndex());
		}
		if (DmgData.Cause.HasEntity())
		{
			JsonDamageEvent->SetStringField("causer", DmgData.Cause.GetPrimaryEntity().ToString(World));
		}
		if (DmgData.Cause.HasNode())
		{
			JsonDamageEvent->SetStringField("node", DmgData.Cause.GetPrimaryNode().ToString(World));
		}
		for (UNetTickComponent* Component : DmgData.Cause.GetPrimaryNodes<UNetTickComponent>(World))
		{
			if (ItemData.Contains(Component->GetClass()))
			{
				JsonDamageEvent->SetStringField("item", NodeClassToString(Component->GetClass()));
				break;
			}
		}
		JsonEventList.Add(JsonDamageEvent);
	}
}


FString ToString(EAxisOption::Type Axis)
{
	if (Axis == EAxisOption::X) 	return "X";
	if (Axis == EAxisOption::Y) 	return "Y";
	if (Axis == EAxisOption::Z) 	return "Z";
	if (Axis == EAxisOption::X_Neg) return "-X";
	if (Axis == EAxisOption::Y_Neg) return "-Y";
	if (Axis == EAxisOption::Z_Neg) return "-Z";
	return "CUSTOM";
}
static TSharedPtr<FJsonObject> MakeSimpleJsonPlayerEvent(FString Name, const FNetTickEvent& Event, FNetTickPlayerId PlayerId)
{
	TSharedPtr<FJsonObject> JsonEvent = MakeShared<FJsonObject>();
	JsonEvent->SetStringField("name", Name);
	JsonEvent->SetNumberField("stamp", Event.Stamp);
	JsonEvent->SetNumberField("player", PlayerId.GetIndex());
	return JsonEvent;
}
void UReplayDriver_GameStats::OnPushEvent(const UNetTickWorld* World, const FNetTickEvent& Event)
{
	static const TSet<FName> SimpleEvents = {
		"Surface Lock",
		"Push Off",
		"Melee",
		"Kick",
		"Start Reload",
		"Finish Reload",
		"Cancel Reload",
		"Burst",
		"Pump",
		"Catch",
		"Throw",
		"Cast",
		"Retract",
		"Start Load",
		"Finish Load",
		"Impulsive Fire",
		"Swing",
		"Stab",
		"Block",
		"Stun",
		"Projectile Slice",
		"Teleport",
		"Expire",
		"Toss",
		"Trigger",
	};

	
	if (Event.Name == UNTGameMode::Event_PlayerElimination)
	{
		HandleEliminationEvent(World, Event);
	}
	else if (Event.Name == "Damage")
	{
		HandleDamageEvent(World, Event);
	}
	else if (Event.Name == "Dash")
	{
		const UNTAstronaut* NTAstronaut = World->GetNode<UNTDash>(Event.NodeId)->GetSibling<UNTAstronaut>();
		if (!NTAstronaut || !NTAstronaut->OwningPlayerId) return;
		FNetTickPlayerId Player = *NTAstronaut->OwningPlayerId;
		if (!OperatingPlayerMap.Contains(Player)) return;
		
		EAxisOption::Type Axis = Event.Data.Get<FNTDashEventData>().Axis;

		PlayerData[OperatingPlayerMap[Player]].NumDashes++;
		if (Axis != EAxisOption::X)
		{
			PlayerData[OperatingPlayerMap[Player]].NumDirectionalDashes++;
		}

		{
			TSharedPtr<FJsonObject> JsonEvent = MakeSimpleJsonPlayerEvent("dash", Event, Player);
			JsonEvent->SetStringField("dir", ToString(Axis));
			JsonEventList.Add(JsonEvent);
		}
	}
	else if (Event.Name == "Equip")
	{
		const UNTAstronaut* NTAstronaut = World->GetFirstComponentOfClass<UNTAstronaut>(*Event.EntityId);
		TSharedPtr<FJsonObject> JsonEvent = MakeSimpleJsonPlayerEvent("equip", Event, *NTAstronaut->OwningPlayerId);
		JsonEvent->SetStringField("item", NodeClassToString(World->GetNode(Event.NodeId)->GetClass()));
		JsonEventList.Add(JsonEvent);
	}
	else if (Event.Name == "Fire")
	{
		if (const UNTGun* Gun = World->GetNode<UNTGun>(Event.NodeId))
		{
			TSharedPtr<FJsonObject> JsonEvent = MakeSimpleJsonPlayerEvent("fire", Event, *Gun->GetInstigatorPlayer());
			const FNTGunFireEventData& FireData = Event.Data.Get<FNTGunFireEventData>();
			JsonEvent->SetStringField("damager", FireData.Projectile.ToString(World));
			JsonEvent->SetField("origin", VecToJson(FireData.Origin, 0));
			JsonEvent->SetField("dir", DirToJson(FireData.Direction));
			JsonEventList.Add(JsonEvent);
		}
		else if (const UNTNightshade* Nightshade = World->GetNode<UNTNightshade>(Event.NodeId))
		{
			TSharedPtr<FJsonObject> JsonEvent = MakeSimpleJsonPlayerEvent("fire", Event, *Nightshade->GetInstigatorPlayer());
			const FNTNightshadeFireEventData& FireData = Event.Data.Get<FNTNightshadeFireEventData>();
			JsonEvent->SetStringField("damager", Event.EntityId->ToString(World));
			JsonEvent->SetField("origin", VecToJson(FireData.Origin, 0));
			JsonEvent->SetField("dir", DirToJson(FireData.Direction));
			JsonEventList.Add(JsonEvent);
		}
	}
	else if (Event.Name == "Shotgun Fire")
	{
		const UNTSledge* Sledge = World->GetNode<UNTSledge>(Event.NodeId);
		TSharedPtr<FJsonObject> JsonEvent = MakeSimpleJsonPlayerEvent("fire", Event, *Sledge->GetInstigatorPlayer());
		JsonEvent->SetStringField("damager", Event.EntityId->ToString(World));
		const FNTSledgeBuckshotEventData& FireData = Event.Data.Get<FNTSledgeBuckshotEventData>();
		FVector AvgDir(0), AvgLoc(0);
		for (const FNTGunFireEventData& EFD : FireData.FireEvents) { AvgDir += EFD.Direction; AvgLoc += EFD.Origin; }
		JsonEvent->SetField("origin", VecToJson(AvgLoc / FireData.FireEvents.Num(), 0));
		JsonEvent->SetField("dir", DirToJson(AvgDir / FireData.FireEvents.Num()));
		JsonEventList.Add(JsonEvent);
	}
	else if (Event.Name == "Release Star")
	{
		FNetTickPlayerId Player = GetEventPlayer(Event, World);
		TSharedPtr<FJsonObject> JsonEvent = MakeSimpleJsonPlayerEvent("fire", Event, Player);
		JsonEvent->SetStringField("damager", Event.EntityId.ToString(World));
		JsonEvent->SetField("origin", VecToJson(World->GetSystem<UNTPhzEngine>()->GetLocation(*Event.EntityId), 0));
        JsonEvent->SetField("dir", DirToJson(FRotator(World->GetInputForPlayer(Player).Rotation).Vector()));
		JsonEventList.Add(JsonEvent);
	}
	else if (Event.Name == "Explosive Fire")
	{
		const FNTRocketLauncherFireData& EventData = Event.Data.Get<FNTRocketLauncherFireData>();
		TSharedPtr<FJsonObject> JsonEvent = MakeSimpleJsonPlayerEvent("fire", Event, GetEventPlayer(Event, World));
		JsonEvent->SetStringField("damager", EventData.Rocket.ToString(World));
		JsonEvent->SetField("origin", VecToJson(EventData.Origin, 0));
		JsonEvent->SetField("dir", DirToJson(EventData.Direction));
		JsonEventList.Add(JsonEvent);
	}
	else if (Event.Name == "Explode")
	{
		if (const UNTRocketComponent* Rocket = World->GetNode<UNTRocketComponent>(Event.NodeId))
		{
			FNetTickPlayerId Player = *World->GetSystem<UNTInstigationTracker>()->GetInstigator(*Event.EntityId).Player;
			TSharedPtr<FJsonObject> JsonEvent = MakeSimpleJsonPlayerEvent("explode", Event, Player);
			JsonEvent->SetField("loc", VecToJson(World->GetSystem<UNTPhzEngine>()->GetLocation(*Event.EntityId), 0));
			JsonEventList.Add(JsonEvent);
		}
	}
	else if (Event.Name == "King Change")
	{
		const FNTKingChangeEventData& KingData = Event.Data.Get<FNTKingChangeEventData>();
		{
			TSharedPtr<FJsonObject> JsonKingChangeEvent = MakeShared<FJsonObject>();
			JsonKingChangeEvent->SetStringField("name", "kingchange");
			JsonKingChangeEvent->SetNumberField("stamp", Event.Stamp);
			if (KingData.PrevKing)
			{
				JsonKingChangeEvent->SetNumberField("oldking", KingData.PrevKing->GetIndex());
			}
			JsonKingChangeEvent->SetNumberField("newking", KingData.NewKing.GetIndex());
			JsonEventList.Add(JsonKingChangeEvent);
		}
	}
	else if (Event.Name == "Spawn Player")
	{
		TotalSpawns++;
		
		JsonEventList.Add(MakeSimpleJsonPlayerEvent("spawn", Event, Event.Data.Get<FNTGameModeSpawnPlayerEventData>().Player));
	}
	else if (Event.Name == "Set Team")
	{
		TSharedPtr<FJsonObject> JsonEvent = MakeSimpleJsonPlayerEvent("set_team", Event, Event.Data.Get<FNTGameModeSetPlayerTeamData>().Player);
		JsonEvent->SetNumberField("team", Event.Data.Get<FNTGameModeSetPlayerTeamData>().Team.GetRawValue());
		JsonEventList.Add(JsonEvent);
	}
	else if (SimpleEvents.Contains(Event.Name))
	{
		JsonEventList.Add(MakeSimpleJsonPlayerEvent(Event.Name.ToString().ToLower().Replace(TEXT(" "), TEXT("_")), Event, GetEventPlayer(Event, World)));
	}



	
	
	if (Event.Name == "Stab")
	{
		SwordStartStabLocation.Add(Event.NodeId, World->GetSystem<UNTPhzEngine>()->GetLocation(World->GetNode<UNTSwordRemote>(Event.NodeId)->GetEntityId()));
	}
	else if (Event.Name == "Kick")
	{
		FNetTickPlayerId Player = GetEventPlayer(Event, World);
		if (OperatingPlayerMap.Contains(Player))
		{
			PlayerData[OperatingPlayerMap[Player]].NumKicks++;
		}
	}
}

void UReplayDriver_GameStats::OnSimulatedTick(const UNetTickWorld* World)
{
	Super::OnSimulatedTick(World);

	if (World->GetSystem<UNTGameMode>()->HasReachedEndCondition() && !bReachedEndCondition)
	{
		bReachedEndCondition = true;
		if (World->GetSystem<UNTGameMode>()->PlayerMap.Num() > 0)
		{
			if (UNTGameMode_TeamDeathmatch* TDM = World->GetSystem<UNTGameMode_TeamDeathmatch>())
			{
				GameJson->SetNumberField("winning team", TDM->GetWinningTeam().GetRawValue());
			}
			else if (UNTGameMode_FreeForAll* FFA = World->GetSystem<UNTGameMode_FreeForAll>())
			{
				GameJson->SetStringField("winner", OperatingPlayerMap[FFA->GetWinningPlayer()]);
			}
			else if (UNTGameMode_King* King = World->GetSystem<UNTGameMode_King>())
			{
				if (King->King) GameJson->SetStringField("winner", OperatingPlayerMap[*King->King]);
				else GameJson->SetStringField("winner", "None");
			}
			else if (UNTGameMode_GunGame* GunGame = World->GetSystem<UNTGameMode_GunGame>())
			{
				GameJson->SetStringField("winner", OperatingPlayerMap[GunGame->GetPlayerRankList()[0]]);
			}
		}
	}

	for (const UNetTickEffect* Effect : World->GetEffects())
	{
		if (const UNTModifyPlayerDataEffect* ModifyPD = Cast<UNTModifyPlayerDataEffect>(Effect))
		{
			for (const TTuple<FNetTickPlayerId, UNTPlayersConfig::FPlayerData>& MPD : ModifyPD->GetAddPlayerData())
			{
				TSharedPtr<FJsonObject> SelectLoadoutEvent = MakeShared<FJsonObject>();
				SelectLoadoutEvent->SetStringField("name", "set_loadout");
				SelectLoadoutEvent->SetNumberField("stamp", World->GetStamp());
				
				SelectLoadoutEvent->SetNumberField("player", MPD.Key.GetIndex());
				TArray<TSharedPtr<FJsonValue>> LoadoutArray;
				for (const UClass* Class : MPD.Value.LoadoutItemRemoteClasses)
				{
					LoadoutArray.Add(MakeShared<FJsonValueString>(NodeClassToString(Class)));
				}
				SelectLoadoutEvent->SetArrayField("items", LoadoutArray);
		
				JsonEventList.Add(SelectLoadoutEvent);
			}
		}
	}

	if (PlayerLeaveBuffer.Contains(World->GetStamp()))
	{
		for (const auto& Leave : PlayerLeaveBuffer[World->GetStamp()])
		{
			OperatingPlayerMap.Remove(Leave.PlayerId);
		}
	}

	if (PlayerJoinBuffer.Contains(World->GetStamp()))
	{
		for (const auto& Join : PlayerJoinBuffer[World->GetStamp()])
		{
			OperatingPlayerMap.Add(Join.PlayerId, Join.Username);
		}
	}

	PrevAstronautHealthMap.Reset();

	UNTGameMode* GM = World->GetSystem<UNTGameMode>();
	for (int i = 0; i < GM->PlayerMap.Num(); i++)
	{
		const FNetTickPlayerId Player = GM->PlayerMap.GetIds()[i];
		if (OperatingPlayerMap.Contains(Player))
		{
			FString Username = OperatingPlayerMap[Player];

			PlayerData[Username].NumPlayTicks++;

			if (GM->PlayerMap.GetDatas()[i].Astronaut)
			{
				const UNTAstronaut* NTAstronaut = GM->PlayerMap.GetDatas()[i].Astronaut->GetComponent<UNTAstronaut>(GM);

				const uint32 Health = World->GetSystem<UNTHealthManager>()->GetHealth(*GM->PlayerMap.GetDatas()[i].Astronaut);
				const FVector Location = World->GetSystem<UNTPhzEngine>()->GetLocation(*GM->PlayerMap.GetDatas()[i].Astronaut);
				const FRotator Rotation = World->GetSystem<UNTPhzEngine>()->GetRotation(*GM->PlayerMap.GetDatas()[i].Astronaut).Rotator();
				const FVector Velocity = World->GetSystem<UNTPhzEngine>()->GetLinearVelocity(*GM->PlayerMap.GetDatas()[i].Astronaut);
				
				PrevAstronautHealthMap.Add(Player, Health);
				LocationAggregatorVolume.AddPoint(Location);

				if ((World->GetStamp() % uint32(0.5 / TICKDT)) == 0)
				{
					PlayerUpdateData.Add({ World->GetStamp(), Player, uint8(Health), Location, Rotation, Velocity });
				}
				
				UNTMagnet* Magnet = GM->PlayerMap.GetDatas()[i].Astronaut->GetComponent<UNTMagnet>(GM);
				bool bMagneting = Magnet && Magnet->State == EMagnetState::SurfaceLock;
				
				if (bMagneting)
				{
					PlayerData[Username].NumTicksMagneting++;
				}
				else
				{
					PlayerData[Username].NumTicksFloating++;
				}
				
				bool bNoInputVector = FVector(World->GetInputForPlayer(Player).Direction).IsZero();
				float Speed = Velocity.Size();
				PlayerData[Username].AverageSpeed.AddValue(Speed);
				if (!bNoInputVector)
				{
					PlayerData[Username].AverageMovingSpeed.AddValue(Speed);
				}


				for (UNetTickComponent* Component : GM->PlayerMap.GetDatas()[i].Astronaut->GetComponents(GM))
				{
					if (ItemData.Contains(Component->GetClass()))
					{
						if (Component->GetNodeId() == NTAstronaut->EquippedItem)
						{
							ItemData[Component->GetClass()].NumTicksEquipped++;
						}
						ItemData[Component->GetClass()].NumTicksUsed++;
					}
				}
			}
		}
	}

	for (const FArchiveChannel_Performance& Perf : PerformanceSnapshots)
	{
		if (Perf.Stamp == World->GetStamp())
		{
			if (Perf.PlayerId && OperatingPlayerMap.Contains(*Perf.PlayerId))
			{
				FString Username = OperatingPlayerMap[*Perf.PlayerId];
				if (PlayerData[Username].PerfCSVLines.IsEmpty())
				{
					PlayerData[Username].PerfCSVLines.Add(FArchiveChannel_Performance::GetCSVHeaderLine());
				}
				PlayerData[Username].PerfCSVLines.Add(Perf.GetCSVLine());
			}
		}
	}
}

void UReplayDriver_GameStats::FinalizeGameJson()
{
	GameJson->SetField("AverageKillDistance", FloatToJson(AggregateAverageKillDistance.ComputeAverage(), 1));
	GameJson->SetNumberField("TotalEliminations", TotalEliminations);
	GameJson->SetNumberField("TotalSpawns", TotalSpawns);

	{
		TSharedPtr<FJsonObject> JsonMiscStats = MakeShared<FJsonObject>();
		JsonMiscStats->SetField("AverageSwordStabKillDistance", FloatToJson(AverageSwordStabKillDistance.ComputeAverage(), 1));
		JsonMiscStats->SetNumberField("NumSwordStabKills", AverageSwordStabKillDistance.Num());
		JsonMiscStats->SetNumberField("ShurikenDropShotKills", ShurikenDropShotKills);
		JsonMiscStats->SetNumberField("ShurikenRegularShotKills", ShurikenRegularShotKills);
		
		GameJson->SetObjectField("misc", JsonMiscStats);
	}
	
	{
		TArray<TSharedPtr<FJsonValue>> DeviceProfileArray;
		TSet<FString> AddedDeviceProfileUsernames;
		for (const FArchiveChannel_DeviceProfile& Profile : DeviceProfiles)
		{
			if (!AddedDeviceProfileUsernames.Contains(Profile.Username))
			{
				DeviceProfileArray.Add(MakeShared<FJsonValueObject>(Profile.ToJsonObject()));
				AddedDeviceProfileUsernames.Add(Profile.Username);
			}
		}
		GameJson->SetArrayField(FString("DeviceProfiles"), MoveTemp(DeviceProfileArray));
	}

	TSharedPtr<FJsonObject> JsonPlayerMap = MakeShared<FJsonObject>();
	for (const auto& PlayerTuple : PlayerData)
	{
		TSharedPtr<FJsonObject> JsonPlayer = MakeShared<FJsonObject>();
		JsonPlayer->SetNumberField("Kills", PlayerTuple.Value.NumKills);
		JsonPlayer->SetNumberField("Deaths", PlayerTuple.Value.NumDeaths);
		JsonPlayer->SetField("AvgSpeed", FloatToJson(PlayerTuple.Value.AverageSpeed.ComputeAverage(), 1));
		JsonPlayer->SetField("AvgMovingSpeed", FloatToJson(PlayerTuple.Value.AverageMovingSpeed.ComputeAverage(), 1));
		JsonPlayer->SetField("PlayTimeSec", FloatToJson(NetTickUtil::TickToTime(PlayerTuple.Value.NumPlayTicks), 2));
		JsonPlayer->SetField("FloatTimeSec", FloatToJson(NetTickUtil::TickToTime(PlayerTuple.Value.NumTicksFloating), 2));
		JsonPlayer->SetField("MagnetTimeSec", FloatToJson(NetTickUtil::TickToTime(PlayerTuple.Value.NumTicksMagneting), 2));
		JsonPlayer->SetNumberField("Dashes", PlayerTuple.Value.NumDashes);
		JsonPlayer->SetNumberField("DirDashes", PlayerTuple.Value.NumDirectionalDashes);
		JsonPlayer->SetNumberField("Kicks", PlayerTuple.Value.NumKicks);

		JsonPlayerMap->SetObjectField(PlayerTuple.Key, JsonPlayer);
		
		if (!PlayerTuple.Value.PerfCSVLines.IsEmpty())
		{
			FString FilePath = FPaths::ProjectSavedDir() / "StudyResult" / FPaths::MakeValidFileName(FString::Printf(TEXT("Performance_%s_g%llu.csv"), *PlayerTuple.Key, Header.GameId));
			FFileHelper::SaveStringArrayToFile(PlayerTuple.Value.PerfCSVLines, *FilePath);
		}
	}
	GameJson->SetObjectField("Players", JsonPlayerMap);

	TSharedPtr<FJsonObject> JsonItemMap = MakeShared<FJsonObject>();
	for (const auto& ItemT : ItemData)
	{
		TSharedPtr<FJsonObject> JsonItem = MakeShared<FJsonObject>();
		JsonItem->SetField("PlayTime", FloatToJson(NetTickUtil::TickToTime(ItemT.Value.NumTicksUsed), 2));
		JsonItem->SetNumberField("Kills", ItemT.Value.NumKills);
		JsonItem->SetNumberField("Deaths", ItemT.Value.NumDeaths);
		JsonItem->SetNumberField("InvKills", ItemT.Value.NumKillsInInventory);
		JsonItem->SetNumberField("InvDeaths", ItemT.Value.NumDeathsInInventory);
		JsonItem->SetField("AvgKillDist", FloatToJson(ItemT.Value.AverageKillDistance.ComputeAverage(), 1));
		JsonItemMap->SetObjectField(NodeClassToString(ItemT.Key), JsonItem);
	}
	GameJson->SetObjectField("Items", JsonItemMap);

	{
		JsonEventList.StableSort([](const TSharedPtr<FJsonObject>& A, const TSharedPtr<FJsonObject>& B)
		{
			return A->GetNumberField(TEXT("stamp")) < B->GetNumberField(TEXT("stamp"));
		});
		
		TArray<TSharedPtr<FJsonValue>> JsonValueEventList;
		for (const TSharedPtr<FJsonObject>& Event : JsonEventList)
		{
			JsonValueEventList.Add(MakeShared<FJsonValueObject>(Event));
		}   
		GameJson->SetArrayField("events", JsonValueEventList);
	}


	
	FString JsonStringOut;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&JsonStringOut);
	FJsonSerializer::Serialize(GameJson.ToSharedRef(), Writer);
	const FString FilePath = FPaths::ProjectSavedDir() / "StudyResult" / FString::Printf(TEXT("Match_g%llu.json"), Header.GameId);
	FFileHelper::SaveStringToFile(*JsonStringOut, *FilePath);
}

void UReplayDriver_GameStats::Shutdown()
{
	Super::Shutdown();

	if (!ensureAlways(bReachedEndCondition))
	{
		UE_LOG(LogAstroStudy, Error, TEXT("Failed to reach end condition for game = %llu"), Header.GameId);
		return;
	}

	FinalizeGameJson();

// #if UE_SERVER && PLATFORM_LINUX
// 		FString UploadScriptPath = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("Scripts/UploadFileToS3.sh"));
// 		FString S3File = FString::Printf(TEXT("s3://delgoodie-astro-data/studyresult/%s"), *FPaths::GetCleanFilename(StudyResultPath));
// 		ASTRO::RunBashScriptDetached(UploadScriptPath, { StudyResultPath, S3File });
// #endif
	
		// FString StudyResultPath = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / "StudyResult" / FPaths::GetCleanFilename(FString::Printf(TEXT("PlayerData-%s.csv"), *FDateTime::UtcNow().ToString())));
		// FFileHelper::SaveStringArrayToFile(PlayerDataCSV, *StudyResultPath);


	{
		const FString FilePath = FPaths::ProjectSavedDir() / "StudyResult" / FString::Printf(TEXT("LocationAgg_%s_g%llu.bin"), *MapName, Header.GameId);
		FArchive* LocFile = IFileManager::Get().CreateFileWriter(*FilePath);
		LocationAggregatorVolume.Serialize(*LocFile);
		LocFile->Close();
	}

	{
		TArray<FString> RipperAmmoClipCSV = { "Remaining Ammo" };

		for (uint8 Clip : RipperBulletsInClipAtKill)
		{
			RipperAmmoClipCSV.Add(FString::Printf(TEXT("%u"), Clip));
		}

		FString StudyResultPath = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / "StudyResult" / FPaths::GetCleanFilename(FString::Printf(TEXT("RipperElimAmmo_g%llu.csv"), Header.GameId)));
		FFileHelper::SaveStringArrayToFile(RipperAmmoClipCSV, *StudyResultPath);

		// #if UE_SERVER && PLATFORM_LINUX
		// 		FString UploadScriptPath = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("Scripts/UploadFileToS3.sh"));
		// 		FString S3File = FString::Printf(TEXT("s3://delgoodie-astro-data/studyresult/%s"), *FPaths::GetCleanFilename(StudyResultPath));
		// 		ASTRO::RunBashScriptDetached(UploadScriptPath, { StudyResultPath, S3File });
		// #endif
	}


	{
		TArray<FString> PlayerUdpateCSV = { "Stamp, PlayerId, Health, Location.X, Location.Y, Location.Z, Rotation.Pitch, Rotation.Yaw, Rotation.Roll, Velocity.X, Velocity.Y, Velocity.Z" };

		for (const FPlayerUpdateData& PUD : PlayerUpdateData)
		{
			PlayerUdpateCSV.Add(FString::Printf(TEXT("%u, %u, %u, %.0f, %.0f, %.0f, %.0f, %.0f, %.0f, %.0f, %.0f, %.0f"), PUD.Stamp, PUD.PlayerId.GetIndex(), PUD.Health, PUD.Location.X, PUD.Location.Y, PUD.Location.Z, PUD.Rotation.Pitch, PUD.Rotation.Yaw, PUD.Rotation.Roll, PUD.Velocity.X, PUD.Velocity.Y, PUD.Velocity.Z));
		}

		FString StudyResultPath = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / "StudyResult" / FPaths::GetCleanFilename(FString::Printf(TEXT("PlayerUpdate_g%llu.csv"), Header.GameId)));
		FFileHelper::SaveStringArrayToFile(PlayerUdpateCSV, *StudyResultPath);

		// #if UE_SERVER && PLATFORM_LINUX
		// 		FString UploadScriptPath = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("Scripts/UploadFileToS3.sh"));
		// 		FString S3File = FString::Printf(TEXT("s3://delgoodie-astro-data/studyresult/%s"), *FPaths::GetCleanFilename(StudyResultPath));
		// 		ASTRO::RunBashScriptDetached(UploadScriptPath, { StudyResultPath, S3File });
		// #endif
	}
}
