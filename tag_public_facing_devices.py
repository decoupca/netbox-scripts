from dcim.choices import DeviceStatusChoices
from dcim.models import Device
from virtualization.choices import VirtualMachineStatusChoices
from virtualization.models import VirtualMachine
from ipam.choices import IPAddressStatusChoices
from ipam.models import IPAddress
from extras.scripts import *
from extras.models import Tag
import ipaddress
from typing import Union


class TagPublicFacingDevices(Script):
    class Meta:
        name = "Tag Public-Facing Devices"
        description = "Tag public-facing devices based on interface IP addresses"

    tag = ObjectVar(
        model=Tag,
        description="Apply this tag to any device that has at least one public IP address on any interface",
        required=True,
    )

    def is_public(self, addr: IPAddress) -> bool:
        addr = ipaddress.IPv4Interface(addr.address)
        rfc6598 = ipaddress.IPv4Network("100.64.0.0/10")
        if not addr.is_private and addr not in rfc6598:
            return True
        else:
            return False

    def tag_if_has_public(self, device: Device, data) -> Union[Device, None]:
        for interface in device.interfaces.all():
            for addr in interface.ip_addresses.exclude(
                status=IPAddressStatusChoices.STATUS_DEPRECATED
            ).all():
                if self.is_public(addr):
                    if data["tag"].slug not in device.tags.slugs():
                        device.tags.add(data["tag"])
                        device.save()
                        self.log_success(
                            f'{device.name} has public IP {addr.address}, tagged {data["tag"]}'
                        )
                        return device
                    else:
                        self.log_info(
                            f"{device.name} has public IP {addr.address} but already tagged, doing nothing"
                        )
        return None

    def run(self, data, commit):
        tagged_devices = []
        for device in (
            Device.objects.filter(status=DeviceStatusChoices.STATUS_ACTIVE)
            .prefetch_related("interfaces__ip_addresses")
            .all()
        ):
            tagged = self.tag_if_has_public(device, data)
            if tagged:
                tagged_devices.append(tagged)
        return tagged_devices
