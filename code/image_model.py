class ImagePolicyModelSS(common.ResnetBase):
    def __init__(self, backbone, warp=False, pretrained=False, all_branch=False, **kwargs):
        super().__init__(backbone, pretrained=pretrained, input_channel=3, bias_first=False)

        self.c = {
                'resnet18': 512,
                'resnet34': 512,
                'resnet50': 2048
                }[backbone]
        self.warp = warp
        self.rgb_transform = common.NormalizeV2(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )

        self.deconv = nn.Sequential(
            nn.BatchNorm2d(self.c + 128),
            nn.ConvTranspose2d(self.c + 128,256,3,2,1,1),
            nn.ReLU(True),
            nn.BatchNorm2d(256),
            nn.ConvTranspose2d(256,128,3,2,1,1),
            nn.ReLU(True),
            nn.BatchNorm2d(128),
            nn.ConvTranspose2d(128,64,3,2,1,1),
            nn.ReLU(True),
        )

        if warp:
            ow,oh = 48,48
        else:
            ow,oh = 96,40

        self.location_pred = nn.ModuleList([
            nn.Sequential(
                nn.BatchNorm2d(64),
                nn.Conv2d(64,STEPS,1,1,0),
                common.SpatialSoftmax(ow,oh,STEPS),
            ) for i in range(4)
        ])

        self.all_branch = all_branch

    def forward(self, image, velocity=torch.FloatTensor([1.0]), command=torch.FloatTensor([[0,0,0,1]])):
        image= image.to(torch.device('cuda' if torch.cuda.is_available() else 'cpu'))

        if self.warp:
            warped_image = tgm.warp_perspective(image, self.M, dsize=(192, 192))
            resized_image = resize_images(image)
            image = torch.cat([warped_image, resized_image], 1)

        velocity = _speed
        command = _command
        image = self.rgb_transform(image)
        h = self.conv(image)
        b, c, kh, kw = h.size()
        # Late fusion for velocity
        velocity = velocity[...,None,None,None].repeat((1,128,kh,kw))
        h = torch.cat((h, velocity), dim=1)
        h = self.deconv(h)
        location_preds = [location_pred(h) for location_pred in self.location_pred]

        location_preds = torch.stack(location_preds, dim=1)

        location_pred = common.select_branch(location_preds, command)
        location_pred = torch.reshape(location_pred,(1,10))
        if self.all_branch:
            return location_pred, location_preds

        return location_pred